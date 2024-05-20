class PeerINFO:
    def __init__(self, username , password, session_id = -1):
        self.username = username
        self.password = password
        self.count_downloads= 0 
        self.count_failures = 0
        self.token_id= session_id
        self.ip=""
        self.port=""
        
        

    @staticmethod
    def serialize(self):
        # Serialize the Peer_info object into a string
        serialized_info = f"{{username:{self.username},"\
                          f"password:{self.password},"\
                          f"count_downloads:{self.count_downloads},"\
                          f"count_failures:{self.count_failures},"\
                          f"token_id:{self.token_id},"\
                          f"ip:{self.ip},"\
                          f"port:{self.port}}}"
        print(serialized_info)
        return serialized_info

    @staticmethod
    def deserialize(serialized_str):
        # Deserialize a string into a Peer_info object
        serialized_str = serialized_str.strip("{}")
        info_parts = serialized_str.split(",")
        info_dict = {}
        for part in info_parts:
            key, value = part.split(":", 1)
            info_dict[key] = value.strip()
        peer_info = PeerINFO(info_dict['username'], info_dict['password'], info_dict['token_id'])
        peer_info.count_downloads = int(info_dict['count_downloads'])
        peer_info.count_failures = int(info_dict['count_failures'])
        peer_info.ip = info_dict['ip']
        peer_info.port = info_dict['port']
        return peer_info
    
    def __str__(self):
            return f"PeerINFO(username='{self.username}', password='{self.password}', token_id={self.token_id}, ip='{self.ip}', port='{self.port}', count_downloads={self.count_downloads}, count_failures={self.count_failures})"
    
    def __eq__(self , other):
        if isinstance(other,  PeerINFO):
            return  self.username == other.username
        return False
    def __hash__(self):
        return hash(self.username)