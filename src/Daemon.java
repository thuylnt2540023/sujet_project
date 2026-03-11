import java.io.*;
import java.net.*;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.GZIPOutputStream;

public class Daemon {

    private static final int HEARTBEAT_INTERVAL = 5000;
    private static final byte CMD_GET_SIZE = 0;
    private static final byte CMD_GET_FRAGMENT = 1;

    private String clientId;
    private String myHost;
    private String directoryHost;
    private int directoryPort;
    private int daemonPort;
    private File sharedFolder;
    private DirectoryService directory;
    private ServerSocket serverSocket;
    private ExecutorService pool = Executors.newCachedThreadPool();
    private volatile boolean running = true;

    private PrintWriter logWriter;

    public Daemon(String dirHost, int dirPort, int daemonPort, String sharedPath, String myHost) {
        this.directoryHost = dirHost;
        this.directoryPort = dirPort;
        this.daemonPort = daemonPort;
        this.sharedFolder = new File(sharedPath);
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
        if (!sharedFolder.exists()) sharedFolder.mkdirs();

        // Connect to Directory via RMI
        Registry registry = LocateRegistry.getRegistry(directoryHost, directoryPort);
        directory = (DirectoryService) registry.lookup("DirectoryService");

        // Use specified IP, or auto-detect
        String localHost = myHost;
        if (localHost == null || localHost.isEmpty()) {
            localHost = InetAddress.getLocalHost().getHostAddress();
        }
        clientId = localHost + ":" + daemonPort;

        // Setup log file
        new File("logs").mkdirs();
        String logFile = "logs/daemon-" + localHost + "-" + daemonPort + ".log";
        logWriter = new PrintWriter(new FileWriter(logFile, true), true);

        // Register files
        List<String> files = scanFiles();
        directory.register(clientId, localHost, daemonPort, files);
        log("[Daemon " + clientId + "] Started");
        log("[Daemon] Shared folder: " + sharedFolder.getAbsolutePath());
        log("[Daemon] Files: " + files);
        log("[Daemon] Log file: " + logFile);

        // TCP server
        serverSocket = new ServerSocket(daemonPort);
        log("[Daemon] TCP listening on port " + daemonPort);

        // Heartbeat thread
        Thread hb = new Thread(this::heartbeatLoop);
        hb.setDaemon(true);
        hb.start();

        // Shutdown hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            running = false;
            try {
                directory.unregister(clientId);
                serverSocket.close();
            } catch (Exception ignored) {}
            log("[Daemon] Shut down.");
        }));

        // Accept connections
        while (running) {
            try {
                Socket client = serverSocket.accept();
                pool.submit(() -> handleClient(client));
            } catch (IOException e) {
                if (running) log("[Daemon] Accept error: " + e.getMessage());
            }
        }
    }

    private List<String> scanFiles() {
        List<String> files = new ArrayList<>();
        File[] list = sharedFolder.listFiles();
        if (list != null) {
            for (File f : list) {
                if (f.isFile()) files.add(f.getName());
            }
        }
        Collections.sort(files);
        return files;
    }

    private void heartbeatLoop() {
        List<String> lastFiles = new ArrayList<>();
        while (running) {
            try {
                Thread.sleep(HEARTBEAT_INTERVAL);
                List<String> current = scanFiles();
                if (!current.equals(lastFiles)) {
                    directory.heartbeat(clientId, current);
                    lastFiles = current;
                    log("[Daemon] File list updated: " + current);
                } else {
                    directory.heartbeat(clientId, null);
                }
            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                log("[Daemon] Heartbeat error: " + e.getMessage());
            }
        }
    }

    private void handleClient(Socket socket) {
        boolean loadTracked = false;
        String clientAddr = socket.getRemoteSocketAddress().toString();
        try {
            socket.setSoTimeout(30000);
            DataInputStream in = new DataInputStream(new BufferedInputStream(socket.getInputStream()));
            DataOutputStream out = new DataOutputStream(new BufferedOutputStream(socket.getOutputStream()));

            byte command = in.readByte();

            if (command == CMD_GET_SIZE) {
                String filename = in.readUTF();
                File file = resolveFile(filename);
                long size = file != null ? file.length() : -1;
                out.writeLong(size);
                out.flush();
                log("[SERVE] GET_SIZE client=" + clientAddr + " file=" + filename + " size=" + size);

            } else if (command == CMD_GET_FRAGMENT) {
                try { directory.incrementLoad(clientId); } catch (Exception ignored) {}
                loadTracked = true;

                String filename = in.readUTF();
                long offset = in.readLong();
                int length = in.readInt();
                boolean compress = in.readBoolean();

                File file = resolveFile(filename);
                if (file == null) {
                    out.writeInt(-1);
                    out.flush();
                    log("[SERVE] GET_FRAGMENT client=" + clientAddr + " file=" + filename + " status=NOT_FOUND");
                    return;
                }

                long t0 = System.currentTimeMillis();

                try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
                    long remaining = raf.length() - offset;
                    if (remaining <= 0) {
                        out.writeInt(-2);
                        out.flush();
                        log("[SERVE] GET_FRAGMENT client=" + clientAddr + " file=" + filename + " status=BAD_OFFSET");
                        return;
                    }
                    int toRead = (int) Math.min(length, remaining);
                    byte[] data = new byte[toRead];
                    raf.seek(offset);
                    raf.readFully(data);

                    boolean didCompress = false;
                    int sentBytes = data.length;

                    if (compress) {
                        ByteArrayOutputStream baos = new ByteArrayOutputStream();
                        try (GZIPOutputStream gzip = new GZIPOutputStream(baos)) {
                            gzip.write(data);
                        }
                        byte[] compressed = baos.toByteArray();
                        if (compressed.length < data.length) {
                            out.writeInt(0);
                            out.writeBoolean(true);
                            out.writeInt(compressed.length);
                            out.write(compressed);
                            didCompress = true;
                            sentBytes = compressed.length;
                        } else {
                            out.writeInt(0);
                            out.writeBoolean(false);
                            out.writeInt(data.length);
                            out.write(data);
                        }
                    } else {
                        out.writeInt(0);
                        out.writeBoolean(false);
                        out.writeInt(data.length);
                        out.write(data);
                    }
                    out.flush();

                    long elapsed = System.currentTimeMillis() - t0;
                    long speedKBs = elapsed > 0 ? (sentBytes * 1000L / elapsed / 1024) : 0;
                    log("[SERVE] GET_FRAGMENT client=" + clientAddr
                            + " file=" + filename
                            + " offset=" + offset
                            + " len=" + toRead
                            + " compressed=" + didCompress
                            + " sent_bytes=" + sentBytes
                            + " time_ms=" + elapsed
                            + " speed_KB/s=" + speedKBs);
                }
            }
        } catch (Exception e) {
            log("[SERVE] ERROR client=" + clientAddr + " error=" + e.getMessage());
        } finally {
            if (loadTracked) {
                try { directory.decrementLoad(clientId); } catch (Exception ignored) {}
            }
            try { socket.close(); } catch (Exception ignored) {}
        }
    }

    private File resolveFile(String filename) {
        try {
            File file = new File(sharedFolder, filename);
            if (!file.getCanonicalPath().startsWith(sharedFolder.getCanonicalPath())) {
                return null;
            }
            if (file.exists() && file.isFile()) return file;
        } catch (IOException ignored) {}
        return null;
    }

    public static void main(String[] args) {
        String dirHost = args.length > 0 ? args[0] : "localhost";
        int dirPort = args.length > 1 ? Integer.parseInt(args[1]) : 1099;
        String shared = args.length > 2 ? args[2] : "./shared";
        String myHost = args.length > 3 ? args[3] : null;
        int daemonPort = args.length > 4 ? Integer.parseInt(args[4]) : 6000;

        System.out.println("Usage: java Daemon [dirHost] [dirPort] [sharedFolder] [myHost] [daemonPort]");
        System.out.println("  myHost:     IP of this machine (auto-detect if not set)");
        System.out.println("  daemonPort: TCP port for serving fragments (default: 6000)");
        System.out.println("  dirHost=" + dirHost + " dirPort=" + dirPort
                + " shared=" + shared
                + " myHost=" + (myHost != null ? myHost : "auto")
                + " daemonPort=" + daemonPort);

        try {
            new Daemon(dirHost, dirPort, daemonPort, shared, myHost).start();
        } catch (Exception e) {
            System.err.println("[Daemon] Fatal: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
