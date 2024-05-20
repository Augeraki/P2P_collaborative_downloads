from random import randint
import threading
import socket 
from Peer_info import PeerINFO

def delete_records_by_id(data, id_to_remove):
    files_to_delete = []#list of files no peer can provide a fragment of 

    for file, records in list(data.items()):
        # Check if records is a dictionary {token id : (set(), flag)}
        if isinstance(records, dict):
            # If the id_to_remove exists in the records, delete it
            if id_to_remove in records:
                del records[id_to_remove] 

            # If the file's records are now empty, mark the file for deletion
            if not records:
                files_to_delete.append(file)
        else:
            print(f"Unexpected record format for {file}: {records}")

    # Delete the files that are unavailable
    for file in files_to_delete:
        del data[file]


class Tracker:
    def __init__(self) -> None:
        self.registered_peers= set() # a set of the peers that have registered an account with you 
        self.connected_peers = {} #key token_id , other attributes
        self.connections = []
        self.available_files={} #self.available_files{ file1:{token_1 : ({set of pieces}, seederFlag), token_2 : ({set of pieces}, seederFlag)}
        # filename, set/list of token_id(s) of the peers that are the seeders of that file         
        #   
        #   filen: {token_6: {3,2,4,5}, token 1:{1, 11, 1}}
        # }
        self.HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        self.PORT = 65432
        self.shared_directory = "shared_directory"
        self.file_list = set()  

        self.lock = threading.Lock() 
        self.file_frags = {} #file : Total_num_of_frags

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.HOST, self.PORT))
            server_socket.listen()
            print(f"Tracker server listening on {self.HOST}:{self.PORT}")

            while True:
                client_socket, client_address = server_socket.accept()
                print(f"New connection from {client_address}")
                # Start a new thread to handle the connection
                threading.Thread(target=self.handle_client, args=(client_socket,client_address)).start()

    def handle_client(self, client_socket , client_address):
        while True:
            try:
                request = client_socket.recv(1024).decode('utf-8')
                if not request:
                    break
                # Parse the request and execute the corresponding action
                if request.startswith("REGISTER"):
                    username, password = request.split()[1], request.split()[2] 
                    response = self.register(username, password, client_address)
                    client_socket.sendall(response.encode('utf-8'))

                elif request.startswith("LOGIN"):
                    username, password , client_address, client_socket_args= request.split()[1], request.split()[2], request.split()[3], request.split()[4]
                    response = self.login(username, password, client_address , client_socket_args)
                    print(response)
                    client_socket.sendall(response.encode('utf-8'))
                    # Implement login functionality
                    
                elif request.startswith("LOGOUT"):
                    token_id = request.split()[1]
                    response = self.logout(token_id)
                    client_socket.sendall(response.encode('utf-8'))
                    # Implement logout functionality
                elif request.startswith("INFORM"):
                    token_id = request.split()[1]
                    
                    if token_id in self.connected_peers:
                        self.inform(token_id , request.split()[2:])
                        print(self.available_files)
                        client_socket.sendall("SUCCESSFUL INFORM".encode('utf-8'))
                    else:
                        client_socket.sendall("ERROR: Invalid token_id".encode('utf-8'))
               
                elif request.startswith("LIST"):
                    token_id = request.split()[1]
                    response = self.reply_list(token_id)
                    # Convert the list to a string with each item separated by a space
                    response_str = ' '.join(response)
                    client_socket.sendall(str(response_str).encode('utf-8'))
                    
                elif request.startswith("DETAILS"):
                    # The peer is requesting details about a file
                    _, sessionID, filename = request.split()
                    response = self.reply_details(filename)
                    client_socket.sendall(response.encode('utf-8'))
                elif request.startswith("LOGOUT"):
                    token_id= request.split()[1]
                    response = self.logout(token_id=token_id)
                    client_socket.sendall(response.encode('utf-8'))
                elif request.startswith("NOTIFY"):
                    token_id = request.split()[1]
                    notify_flag = request.split()[2]
                    response = self.notify(token_id, notify_flag, request.split()[3], request.split()[4] , request.split()[5])
                    client_socket.sendall(response.encode('utf-8'))
                    

            except Exception as e:
                print(f"Error handling client request: {e}")
                break

    def notify(self, token_id, flag, filename, receivers_id , fragment):
       
        if flag=="True":
            self.lock.acquire()
            peer = self.connected_peers.get(token_id)
            #increment sender token_id appropriately
            counter = None
            for p in self.registered_peers:
                if p == peer:
                    p.count_downloads += 1
                    #print peer here
                    peer.count_downloads += 1
                    counter = p.count_downloads
                    #self.available_files.get(filename).add(int(receivers_id))
                    #PHASE 2
                    frags  = self.available_files[filename][receivers_id][0]
                    flag = self.available_files[filename][receivers_id][1]
                    if len(frags) == 0:
                        frags = set()
                    frags.add(fragment)
                    if len(frags)== self.file_frags[filename]:
                        flag=True
                    self.available_files[filename][receivers_id] = (frags, flag)

                    print(self.available_files)
                    #PHASE 2
                    #TODO fix this it should add to this token ids set and then check if the receiver peer can now become a new seeder for that file
            self.lock.release()
            print(f"File: {filename} Available from {self.available_files[filename]}")
            return f"FILE DOWNLOADED AND PEER DOWNLOAD COUNT UPDATED TO {str(counter)} ."
        else:
            self.lock.acquire()
            peer = self.connected_peers.get(token_id)
            counter = None
            for p in self.registered_peers:
                if p == peer:
                    p.count_failures += 1
                    peer.count_failures += 1
                    counter = p.count_failures
            self.lock.release()
            return f"FILE DOWNLOAD FAILED AND PEER DOWNLOAD FAILURE COUNT UPDATED TO {str(counter)}"


    def register(self ,username , password, client_address):

        new_peer = PeerINFO(username,password)
        if new_peer in self.registered_peers:
            return "USERNAME ALREADY IN USE.\n PLEASE, INPUT A DIFFERENT ONE."
        else:
            self.lock.acquire()
            # Save the newly registered peer account 
            self.registered_peers.add(new_peer)
            self.lock.release()
            return "SUCCESS"
    def login(self, username , password,client_address, client_socket):
        #check login info
        registered_peer = PeerINFO(username=username,password=password)

        if registered_peer in self.registered_peers:

            if  registered_peer in self.connected_peers.values():
                # if a peer has impoperly disconnected he can login and matain his old session
                for token, peer in self.connected_peers.items():
                    if peer == registered_peer and peer.password == registered_peer.password:
                        return "SUCCESS " + token


            for peer in self.registered_peers:

                if peer == registered_peer: # find a peer with the same username

                    #check for password match 
                    if peer.password == registered_peer.password:
                        #generate session token 
                        token_id =self.generate_tokenID()
                        #assign token_id
                        registered_peer.token_id = token_id
                        #assign port_address
                        self.lock.acquire()
                        registered_peer.ip = str(client_address)#127.0.0.1
                        registered_peer.port = str(client_socket)#6575
                        # assign that id to the local representation and set this peer as active peer
                        self.connected_peers[token_id.strip()] = registered_peer 
                        print("connected :")
                        self.lock.release()
                        return "SUCCESS " + token_id
                    
                    else:
                        return "Incorrect password " + " -1"
                    
        else: 
            return "User does not exist please regitser" + " -1" 
        
    def inform(self, token_id , request):
        files = []
        frags = {}
        for i, part in enumerate(request):
            if i % 2 == 0 :
                #make a list of the files we were informed of 
                files.append(part)
            else:
                # make a dict of a files and  their fragments 
                frags_list = part.split("-")
                frags[files[-1]] = set(frags_list) #last file added has these frags 

        
        for file in files:
            self.lock.acquire()
            # Add the token_id to the set/list of peers that have the file
            if self.available_files.get(file) is None:
                self.available_files[file] = {}  # = {} //phase 2 {file :{ token_id :(set(), True)}}

            self.available_files[file][int(token_id)] = (frags[file] , True) #self.available_files[file][token_id][0].add(int(token_id))
            self.lock.release()
        self.file_frags[file] = len(self.available_files[file][int(token_id)][0]) 
        
    
    def reply_list(self, token_id):
        #list files to requesting peer
        reply_list=[]
        for value in self.available_files.keys(): # for every filename in the available_files dictionary
            if int(token_id) not in self.available_files[value]: # if the token_id is not in the set/list of peers that have the file
                reply_list.append(value) # add the filename to the reply list
            else:
                reply_list.append(value + " (downloaded file)")
        return reply_list # return the list of filenames
    
    def reply_details(self, filename):
        frags = {}  #NEW
        # for a given file name, respond with a list of peers that can provide that file
        peers_info ="["
        if filename in self.available_files:
            peer_ids = list(self.available_files[filename].keys()) #.keys()  #NEW
            for peer_id in peer_ids:
                peer = (self.connected_peers[str(peer_id)])
                #this is where we save the counters 
                #saving the counters in the connected peers leads to them not persisting
                frags[peer_id] = self.available_files[filename][peer_id]  #NEW
                peers_info += PeerINFO.serialize(peer) + "|"
            peers_info = peers_info[:-1] # remove the last "|"
        peers_info += "]"
        #peers_info += f"FRAGMENT_SEPARATOR{frags}"#NEW
        peers_info += f"???{frags}"
        if peers_info == "[]":
            return "FILE DOES NOT EXIST"
        return peers_info

    def logout(self, token_id):
        
        if token_id in self.connected_peers.keys():
            del self.connected_peers[token_id]
        
            delete_records_by_id(self.available_files , int(token_id))
            print(self.available_files) # remove
            return "SUCCESSFUL LOGOUT"
        else:
            return "USER NOT SIGNED IN ERROR"
                
    def generate_tokenID(self)-> str:
        rand = randint(0,1000)
        while(rand in self.connected_peers.keys()):
            rand = randint(0,1000)
        return str(rand)
    def CheckActive(self , peerIP , peerport):#NOTE not used but works
        try:
            with socket.socket(socket.AF_INET , socket.SOCK_STREAM) as s:
                s.connect((peerIP , peerport))
                # NOTE Set a timeout of 5 seconds for the socket connection
                s.settimeout(5)
                message = f"CHECK_ACTIVE"
                s.sendall(message.encode('utf-8'))
                response = s.recv(1024).decode('utf-8')
                return response
        except socket.timeout:
            return "Connection timed out"
        except ConnectionRefusedError:
            return "Peer is not reachable"
        except Exception as e:
            return f"An error occurred: {e}"

def main():
    while True:
        tracker = Tracker()
        tracker.start()

main()



#Task 1 shut peer server socket 
#Task 2 Test and simulate download failure