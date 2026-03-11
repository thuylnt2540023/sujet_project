import java.io.*;
import java.net.InetAddress;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.text.SimpleDateFormat;
import java.util.Date;

public class Directory {

    private static PrintWriter logWriter;

    static synchronized void log(String msg) {
        String line = "[" + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new Date()) + "] " + msg;
        System.out.println(line);
        if (logWriter != null) {
            logWriter.println(line);
            logWriter.flush();
        }
    }

    public static void main(String[] args) {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 1099;
        String myHost = args.length > 1 ? args[1] : null;

        try {
            // Setup log file
            new File("logs").mkdirs();
            String host = (myHost != null && !myHost.isEmpty()) ? myHost : InetAddress.getLocalHost().getHostAddress();
            String logFile = "logs/directory-" + host + "-" + port + ".log";
            logWriter = new PrintWriter(new FileWriter(logFile, true), true);

            DirectoryServiceImpl dir = new DirectoryServiceImpl();
            Registry registry = LocateRegistry.createRegistry(port);
            registry.rebind("DirectoryService", dir);
            log("[Directory] RMI server started on " + host + ":" + port);
            log("[Directory] Log file: " + logFile);
            log("[Directory] Waiting for clients...");

            Thread.currentThread().join();
        } catch (Exception e) {
            System.err.println("[Directory] Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
