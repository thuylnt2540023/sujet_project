import java.io.Serializable;

public class ClientInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    public String clientId;
    public String host;
    public int port;
    public int load;

    public ClientInfo(String clientId, String host, int port) {
        this.clientId = clientId;
        this.host = host;
        this.port = port;
        this.load = 0;
    }

    public String toString() {
        return clientId + " [load=" + load + "]";
    }
}
