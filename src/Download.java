import java.io.*;
import java.net.*;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.zip.GZIPInputStream;

public class Download {

    private static final byte CMD_GET_SIZE = 0;
    private static final byte CMD_GET_FRAGMENT = 1;
    private static final int MAX_RETRIES = 3;

    private String filename;
    private String directoryHost;
    private int directoryPort;
    private String outputFolder;
    private boolean useCompression;
    private int fragmentSize;
    private String myHost;
    private DirectoryService directory;

    private PrintWriter logWriter;

    // Per-source stats
    private ConcurrentHashMap<String, AtomicLong> sourceBytes = new ConcurrentHashMap<>();
    private ConcurrentHashMap<String, AtomicLong> sourceTime = new ConcurrentHashMap<>();
    private ConcurrentHashMap<String, AtomicInteger> sourceFragCount = new ConcurrentHashMap<>();

    public Download(String filename, String dirHost, int dirPort,
                    String outputFolder, boolean compress, int fragmentSize, String myHost) {
        this.filename = filename;
        this.directoryHost = dirHost;
        this.directoryPort = dirPort;
        this.outputFolder = outputFolder;
        this.useCompression = compress;
        this.fragmentSize = fragmentSize;
        this.myHost = myHost;
    }

    private synchronized void log(String msg) {
        String line = "[" + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new Date()) + "] " + msg;
        System.out.println(line);
        if (logWriter != null) {
            logWriter.println(line);
            logWriter.flush();
        }
    }

    public void start() throws Exception {
        // Setup log file
        new File("logs").mkdirs();
        String localHost = (myHost != null && !myHost.isEmpty()) ? myHost : InetAddress.getLocalHost().getHostAddress();
        String logFile = "logs/download-" + localHost + "-" + filename + ".log";
        logWriter = new PrintWriter(new FileWriter(logFile, true), true);

        // Connect to Directory
        Registry registry = LocateRegistry.getRegistry(directoryHost, directoryPort);
        directory = (DirectoryService) registry.lookup("DirectoryService");

        // Get sources (sorted by load)
        List<ClientInfo> sources = directory.getSourcesForFile(filename);
        if (sources.isEmpty()) {
            log("[Download] No sources found for: " + filename);
            return;
        }
        log("[Download] === START === file=" + filename + " fragment_size=" + fragmentSize
                + " compression=" + useCompression);
        log("[Download] Sources:");
        for (ClientInfo s : sources) {
            log("[Download]   " + s);
        }

        // Get file size
        long fileSize = -1;
        for (ClientInfo src : sources) {
            fileSize = getFileSize(src);
            if (fileSize >= 0) break;
        }
        if (fileSize < 0) {
            log("[Download] Cannot get file size.");
            return;
        }
        log("[Download] File size: " + fileSize + " bytes (" + (fileSize / 1024) + " KB)");

        // Create output file
        File outDir = new File(outputFolder);
        if (!outDir.exists()) outDir.mkdirs();
        File outFile = new File(outDir, filename);
        RandomAccessFile raf = new RandomAccessFile(outFile, "rw");
        raf.setLength(fileSize);

        // Build fragment list
        List<long[]> fragments = new ArrayList<>();
        long off = 0;
        while (off < fileSize) {
            int len = (int) Math.min(fragmentSize, fileSize - off);
            fragments.add(new long[]{off, len});
            off += len;
        }
        log("[Download] Fragments: " + fragments.size() + " x " + (fragmentSize / 1024) + "KB"
                + ", sources: " + sources.size());

        // Shared queue
        ConcurrentLinkedQueue<Integer> queue = new ConcurrentLinkedQueue<>();
        for (int i = 0; i < fragments.size(); i++) queue.offer(i);

        ConcurrentHashMap<Integer, AtomicInteger> retries = new ConcurrentHashMap<>();
        AtomicLong downloaded = new AtomicLong(0);
        AtomicInteger failed = new AtomicInteger(0);
        long startTime = System.currentTimeMillis();

        // Wave 1
        runWorkers(sources, fragments, queue, retries, raf, fileSize, downloaded, failed);

        // Wave 2 if needed
        if (!queue.isEmpty()) {
            log("[Download] " + queue.size() + " fragments left, fetching fresh sources...");
            List<ClientInfo> fresh = directory.getSourcesForFile(filename);
            if (!fresh.isEmpty()) {
                runWorkers(fresh, fragments, queue, retries, raf, fileSize, downloaded, failed);
            }
        }

        raf.close();

        // === SUMMARY ===
        long elapsed = System.currentTimeMillis() - startTime;
        long speedKBs = elapsed > 0 ? (fileSize * 1000L / elapsed / 1024) : 0;

        log("[SUMMARY] ============================================");
        log("[SUMMARY] file=" + filename);
        log("[SUMMARY] file_size=" + fileSize + " bytes");
        log("[SUMMARY] fragment_size=" + fragmentSize + " bytes (" + (fragmentSize / 1024) + " KB)");
        log("[SUMMARY] total_fragments=" + fragments.size());
        log("[SUMMARY] sources_used=" + sources.size());
        log("[SUMMARY] compression=" + useCompression);
        log("[SUMMARY] total_time_ms=" + elapsed);
        log("[SUMMARY] avg_speed_KB/s=" + speedKBs);
        log("[SUMMARY] failed_fragments=" + failed.get());

        // Per-source breakdown
        log("[SUMMARY] --- Per-source stats ---");
        for (Map.Entry<String, AtomicInteger> e : sourceFragCount.entrySet()) {
            String src = e.getKey();
            int count = e.getValue().get();
            long bytes = sourceBytes.getOrDefault(src, new AtomicLong(0)).get();
            long time = sourceTime.getOrDefault(src, new AtomicLong(0)).get();
            long srcSpeed = time > 0 ? (bytes * 1000L / time / 1024) : 0;
            log("[SUMMARY] source=" + src + " fragments=" + count
                    + " bytes=" + bytes + " time_ms=" + time + " speed_KB/s=" + srcSpeed);
        }
        log("[SUMMARY] ============================================");

        log("[Download] Output: " + outFile.getAbsolutePath());
        if (failed.get() > 0) {
            log("[Download] WARNING: " + failed.get() + " fragment(s) failed!");
        }
    }

    private void runWorkers(List<ClientInfo> sources, List<long[]> fragments,
                            ConcurrentLinkedQueue<Integer> queue,
                            ConcurrentHashMap<Integer, AtomicInteger> retries,
                            RandomAccessFile raf, long fileSize,
                            AtomicLong downloaded, AtomicInteger failed) throws InterruptedException {
        List<Thread> workers = new ArrayList<>();
        for (ClientInfo source : sources) {
            Thread t = new Thread(() -> {
                while (true) {
                    Integer idx = queue.poll();
                    if (idx == null) break;

                    long[] frag = fragments.get(idx);
                    long fragOff = frag[0];
                    int fragLen = (int) frag[1];

                    try {
                        long t0 = System.currentTimeMillis();
                        byte[] data = downloadFragment(source, fragOff, fragLen);
                        long fragTime = System.currentTimeMillis() - t0;

                        synchronized (raf) {
                            raf.seek(fragOff);
                            raf.write(data);
                        }

                        long done = downloaded.addAndGet(fragLen);
                        int pct = (int) (done * 100 / fileSize);

                        // Track per-source stats
                        String srcId = source.clientId;
                        sourceBytes.computeIfAbsent(srcId, k -> new AtomicLong(0)).addAndGet(fragLen);
                        sourceTime.computeIfAbsent(srcId, k -> new AtomicLong(0)).addAndGet(fragTime);
                        sourceFragCount.computeIfAbsent(srcId, k -> new AtomicInteger(0)).incrementAndGet();

                        long fragSpeed = fragTime > 0 ? (fragLen * 1000L / fragTime / 1024) : 0;
                        log("[FRAG] idx=" + idx
                                + " offset=" + fragOff
                                + " len=" + fragLen
                                + " source=" + srcId
                                + " time_ms=" + fragTime
                                + " speed_KB/s=" + fragSpeed
                                + " progress=" + pct + "%");

                    } catch (Exception e) {
                        AtomicInteger rc = retries.computeIfAbsent(idx, k -> new AtomicInteger(0));
                        if (rc.incrementAndGet() <= MAX_RETRIES) {
                            queue.offer(idx);
                        } else {
                            failed.incrementAndGet();
                            log("[FRAG] idx=" + idx + " FAILED permanently");
                        }
                        log("[FRAG] idx=" + idx + " ERROR source=" + source.clientId
                                + " error=" + e.getMessage());
                        break;
                    }
                }
            });
            t.setName("dl-" + source.clientId);
            workers.add(t);
        }

        for (Thread t : workers) t.start();
        for (Thread t : workers) t.join();
    }

    private long getFileSize(ClientInfo source) {
        try (Socket sock = new Socket(source.host, source.port)) {
            sock.setSoTimeout(10000);
            DataOutputStream out = new DataOutputStream(sock.getOutputStream());
            DataInputStream in = new DataInputStream(sock.getInputStream());
            out.writeByte(CMD_GET_SIZE);
            out.writeUTF(filename);
            out.flush();
            return in.readLong();
        } catch (Exception e) {
            log("[Download] Size error from " + source + ": " + e.getMessage());
            return -1;
        }
    }

    private byte[] downloadFragment(ClientInfo source, long offset, int length) throws Exception {
        try (Socket sock = new Socket(source.host, source.port)) {
            sock.setSoTimeout(30000);
            DataOutputStream out = new DataOutputStream(new BufferedOutputStream(sock.getOutputStream()));
            DataInputStream in = new DataInputStream(new BufferedInputStream(sock.getInputStream()));

            out.writeByte(CMD_GET_FRAGMENT);
            out.writeUTF(filename);
            out.writeLong(offset);
            out.writeInt(length);
            out.writeBoolean(useCompression);
            out.flush();

            int status = in.readInt();
            if (status != 0) throw new IOException("Server status: " + status);

            boolean compressed = in.readBoolean();
            int dataLen = in.readInt();
            byte[] data = new byte[dataLen];
            in.readFully(data);

            if (compressed) {
                ByteArrayInputStream bais = new ByteArrayInputStream(data);
                GZIPInputStream gzip = new GZIPInputStream(bais);
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                byte[] buf = new byte[8192];
                int n;
                while ((n = gzip.read(buf)) > 0) {
                    baos.write(buf, 0, n);
                }
                gzip.close();
                data = baos.toByteArray();
            }

            return data;
        }
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Usage: java Download <filename> [dirHost] [dirPort] [outputFolder] [myHost] [compress] [fragmentKB]");
            System.out.println("  myHost:     IP of this machine, for log filename (auto-detect if not set)");
            System.out.println("  compress:   true/false (default: false)");
            System.out.println("  fragmentKB: fragment size in KB (default: 512)");
            System.out.println("  Example: java Download movie.mp4 192.168.1.100 1099 ./output 192.168.1.20 false 256");
            return;
        }

        String filename = args[0];
        String dirHost = args.length > 1 ? args[1] : "localhost";
        int dirPort = args.length > 2 ? Integer.parseInt(args[2]) : 1099;
        String output = args.length > 3 ? args[3] : "./shared";
        String myHost = args.length > 4 ? args[4] : null;
        boolean compress = args.length > 5 && Boolean.parseBoolean(args[5]);
        int fragmentKB = args.length > 6 ? Integer.parseInt(args[6]) : 512;
        int fragmentSize = fragmentKB * 1024;

        try {
            new Download(filename, dirHost, dirPort, output, compress, fragmentSize, myHost).start();
        } catch (Exception e) {
            System.err.println("[Download] Fatal: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
