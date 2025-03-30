import hashlib
import os
import sys
import pygame
import time
import threading
import requests
from clientNetworkInterface import clientNetworkInterface
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

nodes = []
auth_token = ''
downloaded_audio = []

class Nodes:
    def __init__(self, nodeNumber, nodeType, ip, port):
        self.nodeNumber = nodeNumber
        self.nodeType = nodeType
        self.ip = ip
        self.port = port


class abstractClient:
    def __init__(self, host="10.30.8.62", port=50001):
        self.host = host
        self.port = port
        self.networkHandler = clientNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui, daemon=True)
        self.running = True
        self.exit_flag = threading.Event()
        self.start_menu_choice = 0
        self.start_menu_window = None
        self.login_details_error = None
        self.login_menu_window = None
        self.signup_menu_window = None
        self.user_entered_username = None
        self.user_entered_password = None
        self.music_received_from_server = []
        self.music_is_playing = False
        self.music_is_paused = False


    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server
        while not self.exit_flag.is_set():
            while self.running:
                if self.connection:
                    message = self.connection.iBuffer.get()
                    if message:
                        if message == 'auth':
                            print("Waiting for authentication node to connect..")
                        elif message.startswith('bootstrap'):
                            cmdparts = message.split(":")
                            if len(cmdparts) >= 3:
                                if cmdparts[1] == "cmd":
                                    if cmdparts[2] == "auth":
                                        if len(nodes) < 1:
                                            nodeStatus = cmdparts[3]
                                            if nodeStatus == '0':
                                                print(f"Received command: {message}")
                                                nodeNumber = int(cmdparts[4])
                                                nodeName = cmdparts[5]
                                                nodeIP = cmdparts[6]
                                                nodePort = cmdparts[7]
                                                nodes.append(Nodes(nodeNumber, nodeName, nodeIP, nodePort))
                                                self.authentication_choice()
                                            else:
                                                print("Authentication node not working")
                                                time.sleep(1)
                                                self.start_menu_code()
                                        else:
                                            # Node already exists
                                            self.authentication_choice()
                                    elif cmdparts[2] == "fdn":
                                        print(f"Received token confirmation from bootstrap")
                                        if len(nodes) >= 1:
                                            nodeStatus = cmdparts[3]
                                            if nodeStatus == '0':
                                                print(f"Received command: {message}")
                                                nodeNumber = int(cmdparts[4])
                                                nodeName = cmdparts[5]
                                                nodeIP = cmdparts[6]
                                                nodePort = cmdparts[7]
                                                nodes.append(Nodes(nodeNumber, nodeName, nodeIP, nodePort))
                                                self.main_menu()
                                            else:
                                                print("File distribution node not working")
                                                time.sleep(1)
                                                self.start_menu_code()
                                        else:
                                            print("File distribution node unavailable")
                                            time.sleep(1)
                                            self.start_menu_code()

                                    elif cmdparts[2] == "token":
                                        if cmdparts[3] == "-1":
                                            print("Token unavailable/invalid, connection failure")
                                            time.sleep(1)
                                            self.start_menu_code()

                                    else:
                                        print("error2")

    def process(self):
        self.uiThread.start()
        self.connection = self.networkHandler.start_client(self.host, self.port)
        start_command = "client:cmd:spwn"
        self.connection.oBuffer.put(start_command)
        self.start_menu_code()
        while self.running:
            pass
            if self.connection:
                pass
            else:
                self.running = False

        # stop the network components and the UI thread
        self.connection.oBuffer.put("quit")
        self.networkHandler.quit()
        self.exit_flag.set()
        sys.exit(0)

    def start_menu_code(self):
        time.sleep(1)
        self.start_menu()
        self.start_menu_window.mainloop()
        if self.start_menu_choice == 3:
            self.exit()
            return
        context_option_command = "client:cmd:start_menu:" + str(self.start_menu_choice)
        if self.connection:
            self.connection.oBuffer.put(context_option_command)

    def start_menu(self):
        self.start_menu_window = tk.Tk()
        self.start_menu_window.title('Start Menu')
        self.start_menu_window.geometry('350x200')
        self.start_menu_window.resizable(0, 0)

        start_menu_label = ttk.Label(self.start_menu_window, text="Start Menu", font=('calibri', 25))
        start_menu_label.grid(row=0, column=0, padx=(90, 0))
        login_button = ttk.Button(self.start_menu_window, text="Login", width=20, command=lambda: self.start_menu_button_clicked(1))
        login_button.grid(row=1, column=0, padx=(90, 0), pady=(10, 0))
        signup_button = ttk.Button(self.start_menu_window, text="Signup", width=20, command=lambda: self.start_menu_button_clicked(2))
        signup_button.grid(row=2, column=0, padx=(90, 0), pady=(10, 0))
        exit_button = ttk.Button(self.start_menu_window, width=20, text="Exit",command=lambda: self.start_menu_button_clicked(3))
        exit_button.grid(row=3, column=0, padx=(90, 0), pady=(10, 0))
        self.authentication_error_check()

    def start_menu_button_clicked(self, input):
        if input == 1:
            self.start_menu_choice = 1
        elif input == 2:
            self.start_menu_choice = 2
        elif input == 3:
           self.start_menu_choice = 3
        self.start_menu_window.destroy()
        self.start_menu_window = None

    def authentication_choice(self):
        if self.start_menu_choice == 1:
            self.authenticate_user_data('1')
        elif self.start_menu_choice == 2:
            self.authenticate_user_data('2')
        else:
            print("An internal error has occurred")
            time.sleep(1)
            self.start_menu_code()

    def authenticate_user_data(self, user_choice):
        global nodes
        if len(nodes) > 0:
            auth_ms_node = next((node for node in nodes if node.nodeType == "auth-ms"), None)
            if auth_ms_node is not None:
                ip = auth_ms_node.ip
                port = auth_ms_node.port
                host = f"{ip}:{port}"
                try:
                    authMicroserviceURL = f'http://{host}/validate_user_details' 
                    print()
                    if user_choice == '1':
                        self.login_menu_tkinter_window()
                    elif user_choice == '2':
                        self.signup_menu_tkinter_window()


                    inputted_data = {
                        'user_choice': user_choice,
                        'username': self.user_entered_username,
                        'password': self.user_entered_password
                    }

                    try:
                        response = requests.post(authMicroserviceURL, json=inputted_data,
                                                 timeout=5)
                    except requests.Timeout:
                        print("Request timed out, connection to authentication microserive has closed.")
                        time.sleep(1)
                        print()
                        self.start_menu_code()
                    except requests.RequestException as ex:
                        print(f"Request failed. Error: {ex}")
                        time.sleep(1)
                        print()
                        self.start_menu_code()
                    else:
                        if response.status_code == 200:
                            global auth_token
                            token = response.json()['token']
                            auth_token = token.replace('Token: ', '')
                            print(f"Received authentication token: {auth_token}")
                            print()
                            fdnRqstCmd = f"client:cmd:fdn:{auth_token}"
                            if self.connection:
                                self.connection.oBuffer.put(fdnRqstCmd)
                                time.sleep(3)
                        else:
                            print(f"Failed to retrieve authentication token. Status code: {response.status_code}")
                            time.sleep(1)
                            print()
                            self.start_menu_code()
                except Exception as ex:
                    print("Login failed")
                    self.login_details_error = True
                    time.sleep(1)
                    self.start_menu_code()
            else:
                print(f"An error has occurred")
                time.sleep(1)
                print()
                self.start_menu_code()

    def authentication_error_check(self):
        if self.login_details_error == True:
            messagebox.showerror("Error", "Incorrect Details Entered Try Again")
            self.login_details_error = False


    def login_menu_tkinter_window(self):
        self.login_menu_window = tk.Tk()
        self.login_menu_window.title('Login')
        self.login_menu_window.geometry('300x200')
        self.login_menu_window.resizable(0, 0)

        login_menu_label = ttk.Label(self.login_menu_window, text="Login Menu", font=('calibri', 22))
        login_menu_label.grid(row=0, column=0, padx=(70, 0))
        username_label = ttk.Label(self.login_menu_window, text="Username:", font=('calibri', 9))
        username_label.grid(row=1, column=0, padx=(0, 10), pady=(10, 0))
        username_input = ttk.Entry(self.login_menu_window, font=('calibri', 10), width=20)
        username_input.grid(row=2, column=0, padx=(70, 0), pady=(0, 0))
        password_label = ttk.Label(self.login_menu_window, text="Password:", font=('calibri', 9))
        password_label.grid(row=3, column=0, padx=(0, 20), pady=(10, 0))
        password_input = ttk.Entry(self.login_menu_window, font=('calibri', 10), show="*", width=20)
        password_input.grid(row=4, column=0, padx=(70, 0), pady=(0, 0))
        login_button = ttk.Button(self.login_menu_window, width=24, text="Login",
                                  command=lambda: self.login_details_checker(username_input.get(),
                                                                             password_input.get()))
        login_button.grid(row=5, column=0, padx=(70, 0), pady=(10, 0))

        self.login_menu_window.mainloop()

    def login_details_checker(self, username, password):
        if username and password:
            self.user_entered_username = username
            self.user_entered_password = password
            self.login_menu_window.destroy()
            self.login_menu_window = None
        else:
            messagebox.showerror("Error", "Fill in all the fields")


    def signup_menu_tkinter_window(self):
        self.signup_menu_window = tk.Tk()
        self.signup_menu_window.title('Signup')
        self.signup_menu_window.geometry('300x200')
        self.signup_menu_window.resizable(0, 0)

        signup_menu_label = ttk.Label(self.signup_menu_window, text="Signup Menu", font=('calibri', 22))
        signup_menu_label.grid(row=0, column=0, padx=(70, 0))
        username_label = ttk.Label(self.signup_menu_window, text="Username:", font=('calibri', 9))
        username_label.grid(row=1, column=0, padx=(0, 10), pady=(10, 0))
        username_input = ttk.Entry(self.signup_menu_window, font=('calibri', 10), width=20)
        username_input.grid(row=2, column=0, padx=(70, 0), pady=(0, 0))
        password_label = ttk.Label(self.signup_menu_window, text="Password:", font=('calibri', 9))
        password_label.grid(row=3, column=0, padx=(0, 20), pady=(10, 0))
        password_input = ttk.Entry(self.signup_menu_window, font=('calibri', 10), width=20)
        password_input.grid(row=4, column=0, padx=(70, 0), pady=(0, 0))
        signup_button = ttk.Button(self.signup_menu_window, width=24, text="Sign up",
                                   command=lambda: self.signup_details_checker(username_input.get(),
                                                                              password_input.get()))
        signup_button.grid(row=5, column=0, padx=(70, 0), pady=(10, 0))

        self.signup_menu_window.mainloop()

    def signup_details_checker(self, username, password):
        if username and password:
            self.user_entered_username = username
            self.user_entered_password = password
            self.signup_menu_window.destroy()
            self.signup_menu_window = None
        else:
            messagebox.showerror("Error", "Fill in all the fields")


    def main_menu(self):
        global nodes
        time.sleep(1)
        self.main_menu_window = tk.Tk()
        self.main_menu_window.title('Main Menu')
        self.main_menu_window.geometry('300x200')
        self.main_menu_window.resizable(0, 0)

        login_menu_label = ttk.Label(self.main_menu_window, text="Main Menu", font=('calibri', 22))
        login_menu_label.grid(row=0, column=0, padx=(70, 0))
        music_player_button = ttk.Button(self.main_menu_window, width=24, text="Music Player", command=lambda: self.main_menu_button_press("music_player"))
        music_player_button.grid(row=1, column=0, padx=(70, 0), pady=(10, 0))
        downloadable_music_button = ttk.Button(self.main_menu_window, width=24, text="Download Music", command=lambda: self.main_menu_button_press("download_music"))
        downloadable_music_button.grid(row=2, column=0, padx=(70, 0), pady=(10, 0))
        current_available_nodes = ttk.Button(self.main_menu_window, width=24, text="Nodes Connected To", command=lambda: self.main_menu_button_press("current_connected_to_nodes"))
        current_available_nodes.grid(row=3, column=0, padx=(70, 0), pady=(10, 0))
        logout_button = ttk.Button(self.main_menu_window, width=24, text="Log Out", command=lambda: self.main_menu_button_press("exit"))
        logout_button.grid(row=4, column=0, padx=(70, 0), pady=(10, 0))

        self.main_menu_window.mainloop()

    def main_menu_button_press(self, user_pressed):
        if user_pressed == "download_music":
            self.download_music()
        elif user_pressed == "music_player":
            self.music_player()
        elif user_pressed == "current_connected_to_nodes":
            self.display_connected_to_nodes(nodes)
        elif user_pressed == "exit":
            self.exit()

    def back_to_main_menu(self, back_from):
        if back_from == "dispaly_available_node":
            self.current_available_node_window.withdraw()
            self.main_menu_window.deiconify()
        elif back_from == "music_player":
            self.music_player_window.withdraw()
            self.main_menu_window.deiconify()
        elif back_from == "download_music":
            self.download_music_window.withdraw()
            self.main_menu_window.deiconify()

    def display_connected_to_nodes(self, nodes_array):
        self.main_menu_window.withdraw()
        self.current_available_node_window = tk.Tk()
        self.current_available_node_window.title('Connected Nodes')
        self.current_available_node_window.geometry('750x200')
        self.current_available_node_window.resizable(0, 0)

        connected_nodes_label = ttk.Label(self.current_available_node_window, text="Current Nodes Connected To",font=('calibri', 22))
        connected_nodes_label.grid(row=0, column=0, padx=(50, 0))
        nodes_display_text = tk.Text(self.current_available_node_window, wrap=tk.NONE, width=80, height=5)
        nodes_display_text.grid(row=1, column=0, padx=(50, 0), pady=(10, 0))
        back_button = ttk.Button(self.current_available_node_window, text="back", command=lambda: self.back_to_main_menu("dispaly_available_node"))
        back_button.grid(row=2, column=0, padx=(50, 0), pady=(5, 0))
        

        for node in nodes_array:
            node_to_display = f" Node type: {node.nodeType}, Node IP: {node.ip}, Node port: {node.port}"
            nodes_display_text.insert(tk.END, node_to_display + '\n')

        self.current_available_node_window.mainloop()

    def music_player(self):
        self.main_menu_window.withdraw()
        self.music_player_window = tk.Tk()
        self.music_player_window.title('Music Player')
        self.music_player_window.geometry('250x220')
        self.music_player_window.resizable(0, 0)

        music_folder_path = os.path.join(os.path.dirname(__file__), "music")
        music_files = [i for i in os.listdir(music_folder_path) if os.path.isfile(os.path.join(music_folder_path, i))]
        music_player_label = ttk.Label(self.music_player_window, text="Music Player", font=('calibri', 22))
        music_player_label.grid(row=0, column=0, padx=(0, 0))
        music_name_listbox = tk.Listbox(self.music_player_window, selectmode=tk.SINGLE, width=25, height=10)
        music_name_listbox.grid(row=1, column=0, padx=(10, 100), pady=(5, 0))
        play_button = ttk.Button(self.music_player_window, text="Play", command=lambda: self.play_song(music_name_listbox.curselection()))
        play_button.grid(row=1, column=0, padx=(150, 0), pady=(0, 130))
        pause_button = ttk.Button(self.music_player_window, text="Pause", command=lambda: self.pause_song())
        pause_button.grid(row=1, column=0, padx=(150, 0), pady=(0, 75))
        unpause_button = ttk.Button(self.music_player_window, text="Unpause", command=lambda: self.unpause_song())
        unpause_button.grid(row=1, column=0, padx=(150, 0), pady=(0, 20))
        replay_button = ttk.Button(self.music_player_window, text="Replay", command=lambda: self.replay_song())
        replay_button.grid(row=1, column=0, padx=(150, 0), pady=(35, 0))
        stop_button = ttk.Button(self.music_player_window, text="Stop", command=lambda: self.stop_music())
        stop_button.grid(row=1, column=0, padx=(150, 0), pady=(90, 0))
        back_button = ttk.Button(self.music_player_window, text="Back", command=lambda: self.back_to_main_menu("music_player"))
        back_button.grid(row=1, column=0, padx=(150, 0), pady=(145, 0))

        for song in music_files:
            music_name_listbox.insert(tk.END, song)

        self.music_player_window.mainloop()

    def play_song(self, song_chosen):
        if song_chosen:
            song_number = song_chosen[0]
            music_folder_path = os.path.join(os.path.dirname(__file__), "music")
            music_files = [i for i in os.listdir(music_folder_path) if os.path.isfile(os.path.join(music_folder_path, i))]
            selected_song = music_files[song_number]
            song_file_path = os.path.join(music_folder_path, selected_song)
            pygame.mixer.init()
            pygame.mixer.music.load(song_file_path)
            pygame.mixer.music.play()
            self.music_is_playing = True
        else:
            messagebox.showerror("Music", "Select a song to be played!")

    def pause_song(self):
        if self.music_is_playing:
            pygame.mixer.music.pause()
            self.music_is_playing = False
            self.music_is_paused = True

    def unpause_song(self):
        if self.music_is_paused:
            pygame.mixer.music.unpause()
            self.music_is_playing = True
            self.music_is_paused = False

    def stop_music(self):
        if self.music_is_playing:
            pygame.mixer.music.stop()
            self.music_is_playing = False
            self.music_is_paused = False

    def replay_song(self):
        if self.music_is_playing:
            pygame.mixer.music.rewind()

    def download_music(self):
        self.main_menu_window.withdraw()
        self.get_music_from_server()
        time.sleep(1)

        self.download_music_window = tk.Tk()
        self.download_music_window.title('Download Music')
        self.download_music_window.geometry('400x240')
        self.download_music_window.resizable(0, 0)
        music_folder_path = os.path.join(os.path.dirname(__file__), "music")
        current_music_files = [i for i in os.listdir(music_folder_path) if os.path.isfile(os.path.join(music_folder_path, i))]

        download_music_label = ttk.Label(self.download_music_window, text="Download Music", font=('calibri', 22))
        download_music_label.grid(row=0, column=0, padx=(0, 0))
        downloadable_music_label = ttk.Label(self.download_music_window, text="Downloadable Music", font=('calibri', 12))
        downloadable_music_label.grid(row=1, column=0, padx=(0, 260))
        downloaded_music_label = ttk.Label(self.download_music_window, text="Downloaded Music", font=('calibri', 12))
        downloaded_music_label.grid(row=1, column=0, padx=(215, 0), pady=(0, 0))
        downloadable_music_listbox = tk.Listbox(self.download_music_window, selectmode=tk.SINGLE, width=25, height=10)
        downloadable_music_listbox.grid(row=2, column=0, padx=(10, 260), pady=(5, 0))
        downloadable_music_button = ttk.Button(self.download_music_window, width=10, text="Download", command=lambda: self.download_selected_music(downloadable_music_listbox.curselection()))
        downloadable_music_button.grid(row=2, column=0, padx=(0, 20), pady=(0, 70))
        back_button = ttk.Button(self.download_music_window, width=10, text="Back", command=lambda: self.back_to_main_menu("download_music" ))
        back_button.grid(row=2, column=0, padx=(0, 20), pady=(0, 10))
        self.downloaded_music_listbox = tk.Listbox(self.download_music_window, selectmode=tk.SINGLE, width=25, height=10)
        self.downloaded_music_listbox.grid(row=2, column=0, padx=(220, 10), pady=(5, 0))
        back_button = ttk.Button(self.download_music_window, text="Back")
        back_button.grid(row=7, column=0, padx=(150, 0), pady=(145, 0))

        for music in self.music_received_from_server:
            downloadable_music_listbox.insert(tk.END, music)

        for music in current_music_files:
            self.downloaded_music_listbox.insert(tk.END, music)

    def download_selected_music(self, music_to_download):
        if music_to_download:
            song_number = music_to_download[0]
            song_name = self.music_received_from_server[song_number]
            is_valid = self.is_song_valid(song_name)
            if is_valid is True:
                messagebox.showerror("Error", "Song is already downloaded choose a different one!")
            else:
                print(song_name)
                self.download_from_server(song_name)

        else:
            messagebox.showerror("Error", "Select a song to download from the downloadable music section only!")

    def is_song_valid(self, song):
        music_folder_path = os.path.join(os.path.dirname(__file__), "music")
        current_music_files = [i for i in os.listdir(music_folder_path) if os.path.isfile(os.path.join(music_folder_path, i))]
        if song in current_music_files:
            return True
        else:
            return False
        

    def get_music_from_server(self):
        global nodes
        if len(nodes) > 0:
            fd_ms_node = next((node for node in nodes if node.nodeType == "fd-ms"), None)
            if fd_ms_node is not None:
                ip = fd_ms_node.ip
                port = fd_ms_node.port
                host = f"{ip}:{port}"
                try:
                    print("Sending request to file distribution microservice for music file list")
                    request_music_list_url = f'http://{host}/get_music_to_download'
                    response = requests.get(request_music_list_url)

                    if response.status_code == 200:
                        music_received = response.json().get('music_titles', [])

                        if music_received:
                            self.music_received_from_server = music_received
                            print("Music file successfully received")
                        else:
                            messagebox.showerror('Error','No music was found.')
                    else:
                        print(f'Error could not get music files error status code: {response.status_code}')
                except Exception as e:
                    print(f"Exception occurred: {e}")
        else:
            print("Node unavailable")



    def download_from_server(self, song_to_download):
        global nodes
        if len(nodes) > 0:
            fd_ms_node = next((node for node in nodes if node.nodeType == "fd-ms"), None)
            if fd_ms_node is not None:
                ip = fd_ms_node.ip
                port = fd_ms_node.port
                host = f"{ip}:{port}"
                self.download_bar_display_window(song_to_download, host)
            else:
                print("Node unavailable")
        else:
            print("Node unavailable")

    def download(self, song_to_download, host):
        try:
            self.download_music_window.withdraw()
            download_song_url = f'http://{host}/download_song/{song_to_download}'
            print()
            with requests.get(download_song_url, stream=True) as response:
                if response.status_code == 200:
                    total_size = int(response.headers.get('Content-Length', 0))
                    MD5_checksum = response.headers.get('MD5-Checksum')
                    print(f"MD5 checksum received: {MD5_checksum}")
                    music_folder_location = os.path.join(os.path.dirname(__file__), "music")
                    if not os.path.exists(music_folder_location):
                        os.makedirs(music_folder_location)
                    download_filename = os.path.join(music_folder_location, song_to_download)
                    self.progress_bar["maximum"] = total_size
                    self.progress_bar["value"] = 0
                    with open(download_filename, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=7168):
                            file.write(chunk)
                            self.progress_bar["value"] += len(chunk)
                            self.download_bar_window.update()
                            self.download_bar_window.update_idletasks()
                    MD5_checksum_from_file = hashlib.md5(open(download_filename, 'rb').read()).hexdigest()
                    print(f"Downloaded files MD5 checksum: {MD5_checksum_from_file}")
                    # Verify MD5 checksum
                    if MD5_checksum == MD5_checksum_from_file:
                        print(f'MD5 Checksum successfully matched, {song_to_download} was downloaded successfully')
                        messagebox.showinfo('Success', f'{song_to_download} has been checked with md5 and has been downloaded successfully!')
                        time.sleep(1)
                    else:
                        print('Failed to verify MD5 checksum')
                        messagebox.showerror('Error', f'{song_to_download} Failed to verify MD5 checksum!')
                else:
                    print(f'Failed to download song, error status code: {response.status_code}')
        except Exception as e:
            print(f"Exception occurred: {e}")

        finally:
            self.download_bar_window.withdraw()
            self.download_music()


    def download_bar_display_window(self, song_name, host):
        self.download_bar_window = tk.Tk()
        self.download_bar_window.title("Downloading Music")
        self.download_bar_window.geometry('520x100')
        self.download_bar_window.resizable(0, 0)

        downloading_music_button = ttk.Label(self.download_bar_window, text=f"Downloading {song_name}", font=('calibri',22))
        downloading_music_button.grid(row=0, column=0, padx=(45, 0), pady=(0, 0))
        self.progress_bar = ttk.Progressbar(self.download_bar_window, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=1, column=0, padx=(20, 0), pady=(20, 10))
        self.download(song_name, host)
        self.download_bar_window.mainloop()

    def exit(self):
        self.running = False
        return

if __name__ == "__main__":
    client = abstractClient("10.30.8.62", 50001)
    client.process()