import java.rmi.Remote;
import java.rmi.RemoteException;
import java.util.List;

public interface DirectoryService extends Remote {
    void register(String clientId, String host, int port, List<String> files) throws RemoteException;
    void unregister(String clientId) throws RemoteException;
    void heartbeat(String clientId, List<String> files) throws RemoteException;
    List<ClientInfo> getSourcesForFile(String filename) throws RemoteException;
    void incrementLoad(String clientId) throws RemoteException;
    void decrementLoad(String clientId) throws RemoteException;
}
