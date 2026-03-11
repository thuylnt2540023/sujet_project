import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class DirectoryServiceImpl extends UnicastRemoteObject implements DirectoryService {

    private Map<String, ClientInfo> clients = new ConcurrentHashMap<>();
    private Map<String, Set<String>> fileToClients = new ConcurrentHashMap<>();
    private Map<String, Long> heartbeats = new ConcurrentHashMap<>();

    private static final long TIMEOUT_MS = 15000;

    public DirectoryServiceImpl() throws RemoteException {
        super();
        Thread cleaner = new Thread(() -> {
            while (true) {
                try {
                    Thread.sleep(10000);
                    long now = System.currentTimeMillis();
                    List<String> dead = new ArrayList<>();
                    for (Map.Entry<String, Long> e : heartbeats.entrySet()) {
                        if (now - e.getValue() > TIMEOUT_MS) {
                            dead.add(e.getKey());
                        }
                    }
                    for (String id : dead) {
                        Directory.log("[Directory] Client timed out: " + id);
                        removeClient(id);
                    }
                } catch (InterruptedException e) {
                    break;
                }
            }
        });
        cleaner.setDaemon(true);
        cleaner.start();
    }

    public synchronized void register(String clientId, String host, int port, List<String> files)
            throws RemoteException {
        ClientInfo info = clients.get(clientId);
        if (info == null) {
            info = new ClientInfo(clientId, host, port);
            clients.put(clientId, info);
            Directory.log("[Directory] New client: " + info);
        }

        for (Set<String> set : fileToClients.values()) {
            set.remove(clientId);
        }
        fileToClients.entrySet().removeIf(e -> e.getValue().isEmpty());

        for (String file : files) {
            fileToClients.computeIfAbsent(file, k -> ConcurrentHashMap.newKeySet()).add(clientId);
        }

        heartbeats.put(clientId, System.currentTimeMillis());
        Directory.log("[Directory] " + clientId + " registered " + files.size() + " file(s): " + files);
    }

    public synchronized void unregister(String clientId) throws RemoteException {
        removeClient(clientId);
    }

    public void heartbeat(String clientId, List<String> files) throws RemoteException {
        heartbeats.put(clientId, System.currentTimeMillis());
        if (files != null) {
            ClientInfo info = clients.get(clientId);
            if (info != null) {
                register(clientId, info.host, info.port, files);
            }
        }
    }

    public synchronized List<ClientInfo> getSourcesForFile(String filename) throws RemoteException {
        Set<String> ids = fileToClients.get(filename);
        if (ids == null || ids.isEmpty()) {
            Directory.log("[Directory] Query for '" + filename + "' -> no sources");
            return new ArrayList<>();
        }
        List<ClientInfo> result = new ArrayList<>();
        for (String id : ids) {
            ClientInfo info = clients.get(id);
            if (info != null) {
                ClientInfo copy = new ClientInfo(info.clientId, info.host, info.port);
                copy.load = info.load;
                result.add(copy);
            }
        }
        result.sort(Comparator.comparingInt(c -> c.load));
        Directory.log("[Directory] Query for '" + filename + "' -> " + result.size() + " source(s): " + result);
        return result;
    }

    public void incrementLoad(String clientId) throws RemoteException {
        ClientInfo info = clients.get(clientId);
        if (info != null) {
            synchronized (info) { info.load++; }
        }
    }

    public void decrementLoad(String clientId) throws RemoteException {
        ClientInfo info = clients.get(clientId);
        if (info != null) {
            synchronized (info) { if (info.load > 0) info.load--; }
        }
    }

    private synchronized void removeClient(String clientId) {
        clients.remove(clientId);
        heartbeats.remove(clientId);
        for (Set<String> set : fileToClients.values()) {
            set.remove(clientId);
        }
        fileToClients.entrySet().removeIf(e -> e.getValue().isEmpty());
        Directory.log("[Directory] Removed: " + clientId);
    }
}
