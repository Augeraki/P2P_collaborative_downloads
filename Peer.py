import threading
import socket
from Peer_info import PeerINFO
import os
import time
import sys
import timeit
from random import randint, choice
from time import sleep
from partition import * #our modules for handling the fragmentation and re-construction of file fragments

############################### MISC FUNCS##############################
#misc functions
def parse_fragment_dict(s):
    s= s.strip("{")
    s= s.strip("}")
    #list of key value pairs as strings
    pairs = s.split('), ')

    # Initialize an empty dictionary
    result = {}

    # Iterate over key-value pairs
    for pair in pairs:
        token_id , value_str = pair.split(": ({")
        # Convert key to integer
        token_id = int(token_id.strip())

        # Parse value
       
        value_parts = value_str.split("},")
        frag_list = value_parts[0].split(", ")
        frag_list = [frag.strip("'") for frag in frag_list]
        value_bool = bool(value_parts[1].strip())
        value_set = set(frag_list)
        # Add key-value pair to dictionary
        result[token_id] = (value_set, value_bool)
    
    return result

########################################################################
disconnect_server_flag = None
class Peer:
    def __init__(self, i ) -> None:
        self.session_id = -1 # this means it has not yet connected to the peer
        self.IP = "127.0.0.1" #allow the OS to assign my IP
        self.port = "999"+ str(i) # this is the port The peer accepts server connections to stream files to other peers
        self.username = None
        self.password = None
        self.count_downloads = 0 
        self.count_failures = 0 
        self.secret= randint(0, 100) #used to close server
        self.serverHOST = "127.0.0.1"  # The server's hostname or IP address
        self.serverPORT = 65432  # The port used by the server
        self.shared_folder = "shared_directory/peer"+str(i) # the directory where the peer stores the files it is willing to share 

        self.file_seeder_frags_lookup = partition_allfiles(self.shared_folder) #has the number of fragments of each file we are the seeder of 
        # a dictionary that contains the complete files (files which this Peer instance is the seeder of) and the value is the number of pieces/fragments

        # NOTE (look at notes )make a data structure that keeps track of the fragements given by each peer for each file 
        self.seeder_waitlist = []
        self.fulfil_seeder_serve = False
        self.response_seeder_serve_event = threading.Event()
        self.Seeder_serve_lock = threading.Lock() 
    
    def register(self , username , password):
        """
        This method a suggested username the user has prompted 
        and sends it with his selected password to register to the tracker
        """
        #Connect to the server 
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))

            request = f"REGISTER {username} {password} "
            s.sendall(request.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')

            if response == "SUCCESS":
                self.username = username
                self.password = password
                print("Registration successful")
               
                return True
            else:
                print(f"Registration failed: {response}")
                
                return False
            
    def login(self, username , password):
        #NOTE : not tested and not completely implemented
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))

            request = f"LOGIN {username} {password} {self.IP} {self.port}"
            s.sendall(request.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            if response.split()[0] == "SUCCESS":
               
                print(f"Assigned token_id: {response.split()[1]}")
                
                token=  response.split()[1]
                self.session_id = token # implement parse integer 
                self.inform()
                threading.Thread(target=self.server_action).start()

                return True
            else:
                #self.session_id= response
                print(f"Login failed: {response}")
                return False
            
    def inform(self):
        # Connect to the tracker using the existing socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))

            # Construct the message to send to the tracker
            message = f"INFORM {self.session_id}"

            #Get a list of all the files in the shared directory
            files_in_shared_dir = os.listdir(os.getcwd() + "/" + self.shared_folder)
            print(files_in_shared_dir)
            files_in_shared_dir = [filename for filename in files_in_shared_dir if filename.endswith(".txt")]
            frags =""
            print(self.file_seeder_frags_lookup)
            for file in files_in_shared_dir:
                for i in range(1, self.file_seeder_frags_lookup[file] + 1):
                    if i == self.file_seeder_frags_lookup[file]:
                        frags+=str(i) 
                    else:
                        frags+= (str(i) + "-")
                message += f" {file} {frags}"
                frags= ""
            print(message)

            # Send the message to the tracker
            s.sendall(message.encode('utf-8'))

            # Wait for the tracker's response and handle it accordingly
            response = s.recv(1024).decode('utf-8')
            if response.startswith("SUCCESS"):
                print("\nPeer informed the tracker about its shared files successfully.")
            else:
                print(f"Error informing the tracker: {response}")
    def list(self)-> list:
        # Connect to the tracker using the existing socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))

            # Construct the message to send to the tracker
            message = f"LIST {self.session_id}"

            # Send the message to the tracker
            s.sendall(message.encode('utf-8'))

            response = s.recv(1024).decode('utf-8')
            available_files = response.split()

            if len(available_files) == 0:
                print("No files available.")
            else :
                print("Available files:")
                for file in available_files:
                    print(file)
            return available_files

    def details(self, filename): 
    # Connect to the tracker using the existing socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))
            message = f"DETAILS {self.session_id} {filename}"
            s.sendall(message.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
        
            response_fragments = {}
            if response.strip() != "FILE DOES NOT EXIST" :

                response_fragments = parse_fragment_dict(response.split("???")[1])
                peers_info = response[response.find("[")+1:response.find("]")].split("|")  #NEW
                peers = []
                for peer_info in peers_info:
                    peer = PeerINFO.deserialize(peer_info)
                    peers.append(peer)
                print(response_fragments)
                return peers , response_fragments
            else:
                print(f"Error retrieving the details of the file: {response}")
                return [] , response_fragments
    def logout(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))
            message = f"LOGOUT {self.session_id}"
            s.sendall(message.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            self.close_server()

            return response
    def close_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        
            s.connect((self.IP , int(self.port)))
            message = f"CLOSE {str(self.secret)}"
            s.sendall(message.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            print(response)
    def CheckActive(self , peerIP , peerport):
        try:
            with socket.socket(socket.AF_INET , socket.SOCK_STREAM) as s:
                s.connect((peerIP , peerport))
                # NOTE Set a timeout of 5 seconds for the socket connection
                s.settimeout(500)
                rtt = float('inf')
                message = f"CHECK_ACTIVE"
                start_time = timeit.default_timer()  # Record the start time before sending the message

                s.sendall(message.encode('utf-8'))

                response = s.recv(1024).decode('utf-8')
                end_time = timeit.default_timer()  # Record the end time after receiving the response
                rtt = end_time - start_time  # Calculate the Round Trip Time
                return response[0] , rtt*1000
        except socket.timeout:
            return "Connection timed out" , rtt
        except ConnectionRefusedError:
            return "Peer is not reachable" , rtt
        except Exception as e:
            return f"An error occurred: {e}" 
    def evaluate_peers(self, peers , rtts): # peer[i] took rtts[i] ms to respond
        score_list = []
        for i in range(0,len(peers)):
            score_list.append(rtts[i] *(0.75 * peers[i].count_downloads + 1.25*peers[i].count_failures))
        return score_list
    
    def SimpleDownload(self , filename ): #NOTE implement notify 
        peers = self.details(filename=filename) #add the dictionary
        evaluations = list()

        if len(peers) == 0:
            return f"FILE {filename} NON EXISTENT"
        
        for p in peers:
            response  = self.CheckActive(p.ip , p.port) 
            if response[0].__contains__("POSITIVE_ACK"):
                evaluations.append(response[1]) # only aknowlegde evaluations from active nodes
            else:
                evaluations.append(float('inf')) # remove peers from possible peers , peers that are unavailable

        peers_score_list = self.evaluate_peers(peers, evaluations)#evaluates peers and returns a list with the scores

        for i in range(1, len(peers)):#sorts the peers from the one with the lowest score to the one with the highest
            key = peers_score_list[i]
            peer = peers[i]
            j = i - 1
            while j >= 0 and key < peers_score_list[j]:
                peers[j + 1] = peers[j]
                peers_score_list[j + 1] = peers_score_list[j]
                j -= 1
            peers[j + 1] = peer
            peers_score_list[j + 1] = key

        for p in peers:
            current_peer= p.token_id
            try:
                # Uncomment to simulate download failure
#                raise socket.timeout("Server did not respond within the timeout period.")

                with socket.socket(socket.AF_INET , socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect((p.ip , int(p.port)))
                    message = f"DOWNLOAD {filename}"
                    s.sendall(message.encode('utf-8'))
                    file_path = self.shared_folder + "/" + filename
                    file = open(file_path, 'wb')
                    while True:
                        chunk = s.recv(1024)
                        if "end" in chunk.decode():
                            s.send(str("end").encode())
                            break                      
                        file.write(chunk)
                    file.close()
                    succes = self.notify(current_peer, True, filename, self.session_id)
                    print(succes)
                    return f"SUCCESSFUL DOWNLOAD OF {filename}"
            except ConnectionRefusedError:
                fail = self.notify(current_peer , False, filename, self.session_id)
                print(fail)
                continue
            except socket.timeout:
                fail = self.notify(current_peer , False, filename, self.session_id)
                print(fail)
                continue

        return f"NO PEER COULD SEND YOU {filename}"
     

    def notify(self , peer_token, success_flag, filename, receivers_id, fragment=0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.serverHOST, self.serverPORT))
            message = f"NOTIFY {peer_token} {success_flag} {filename} {receivers_id} {fragment}"
            s.sendall(message.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            #if response contains message that we have every fragment of the file(filename call assemble)

            return response


    def server_action(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.IP, int(self.port)))
            server_socket.listen()
            
            #Method close server after logout
            while True:
                client_socket, client_address = server_socket.accept()
                self.server_sock = client_socket
                print(f"New connection from {client_address}")
                thread = threading.Thread(target=self.handle_peer_conn, args=(client_socket,client_address, server_socket))
                thread.start()

                if disconnect_server_flag:
                    server_socket.close()
                    break                
                

    def handle_peer_conn(self, client_socket , client_address, server_socket):
        global disconnect_server_flag
        while True:
            try:
                request = client_socket.recv(1024).decode('utf-8')
                if not request:
                    break
                # Parse the request and execute the corresponding action
                if request.startswith("CHECK_ACTIVE"):
                    response = f"POSITIVE_ACK {self.session_id}"
                    #break 
                    #NOTE remove '#' to simulate check Active failure
                    client_socket.sendall(response.encode('utf-8'))
                
                elif request.startswith("CLOSE"):
                    if self.secret == int(request.split()[1]):
                        response = "OK"
                        client_socket.sendall(response.encode('utf-8'))
                        disconnect_server_flag = True
                        
                    else:
                        response = "DENIED"
                        client_socket.sendall(response.encode('utf-8'))

                elif request.startswith("DOWNLOAD"):
                    
                    #simulate timeout
                    file_path = self.shared_folder + "/" + request.split()[1]
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as file:
                            data = file.read()
                            while data:
                                
                                client_socket.send(data)
                                data = file.read()
                                if not data:
                                    client_socket.send(str("end").encode())
                                    break
                            print("FILE SENT")
                        

                            # Close the file and connection
                            
                        
                    else:
                        response = "UNAVAILABLE_FILE"
                        client_socket.sendall(response.encode('utf-8')) 
                elif request.startswith("SEEDER-SERVE"):
                    self.Seeder_serve_lock.acquire()
                    self.seeder_waitlist.append((client_socket, client_address))
                    self.Seeder_serve_lock.release()
                    #set the global timer flag 
                    if not self.fulfil_seeder_serve:
                        self.Seeder_serve_lock.acquire()
                        self.fulfil_seeder_serve=True 
                        self.Seeder_serve_lock.release()
                        threading.Timer(0.2, self.select_clients_response).start()
                    
                    #wait until the event is completed
                    self.response_seeder_serve_event.wait()
                    #Event has been completed so respond to each Client accordingly 
                    try:
                        if 'selected' in client_socket.__dict__:
                            pass #response with a random fragment
                            #TODO implement , the response of data
                        else:
                            pass
                            #TODO implement , the response of data
                            #reject seeder serve

                    finally:
                        client_socket.close()
                        self.Seeder_serve_lock.acquire()
                        self.seeder_waitlist.remove((client_socket, client_address))
                        self.Seeder_serve_lock.release()          

            except Exception as e:
                print(f"Error handling client request: {e}")
                break

    def select_clients_response(self):
        if self.seeder_waitlist:
            selected_client = choice(self.seeder_waitlist) #choose a client from the list at random
            selected_client[0].__dict__['selected'] = True #mark the selected socket
            self.response_seeder_serve_event.set() #wake up the process waiting on this event

        #reset global timer flag
        self.fulfil_seeder_serve = False
        self.fulfil_seeder_serve = False
        #reset event flag

    def console_menu(self):
        while True:
            print("\nPeer Menu:")
            print("1. List available files")
            print("2. Download a file")
            print("3. File details")
            print("4. Logout")
            print("5. Exit")

            choice = input("\nEnter your choice (1-5): ")

            if choice == "1":
                self.list()
                
            elif choice == "2":
                filename = input("\nEnter the filename to download: ")
                self.SimpleDownload(filename)
            elif choice == "3":
                filename = input("\nEnter the filename to get peers that host it: ")
                peer_infos = self.details(filename)[0]
                
                for p in peer_infos:
                    print(p)
                    
                    resp, rtt = self.CheckActive(p.ip, int(p.port))
                    
                    print(resp + " TIME TO RESPOND:"+ str(rtt) +" ms")
                    print(self.evaluate_peers([p] , [rtt]))
                #check each peer if they are active evaluate them 
                
                # Get the list of available files
                #peers_info = [] # Get the details of the peers sharing the available files
                #for filename in available_files:
                #    peers_info.extend(self.details(filename))
                #self.share_directory(peers_info)
            elif choice == "4":
                print("\nLogging out...")
                print("\nRESULT "+ self.logout())
                return True
            elif choice == "5":
                print("\nExiting...")
                return False
            else:
                print("\nInvalid choice. Please try again.")

    def registration_menu(self):
        registered = False
        while not registered:
            print("\nRegistration:")
            username = input("Please enter your name: ")
            password = input("Please enter your password: ")
            registered = self.register(username=str(username), password=str(password)) # Register the user
            self.login(username, password) # Automatically login after registration
    
    def login_menu(self):
        logged_in = False
        while not logged_in:
            print("\nLogin:")
            username = input("Please enter your username: ")
            password = input("Please enter your password: ")
            logged_in = self.login(username=str(username), password=str(password)) # Login the user
        


def main():
    
    #num = sys.argv[1]
    while True:
        print("WELCOME TO THE PEER-TO-PEER FILE SHARING SYSTEM !")
        p1 = Peer(1) # Hardcoded FOR DEBUGGING !
        
        decided = False
        while not decided:
            inp = str.capitalize(input("Enter 'R' for registration or 'L' for login: "))
            if inp == 'R':
                p1.registration_menu()
                decided = True
            elif inp == 'L':
                p1.login_menu()
                decided = True
            else:
                print("Invalid input. Please try again.")
        
        while True:
            ans = p1.console_menu()
            if ans == True:
                if p1.logout():
                    print("\nLogged out successfully.")
                    break
            else:
                print("GOODBYE")
                return

main()

