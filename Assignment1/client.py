from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, timeout
from struct import unpack
from server import Packet, Socket, SERVER, INITIAL_PORT, HEADER_LENGTH
from sys import exit
import time

class Client(Socket):
    def __init__(self, server):
        super().__init__(server)
        self.ENTITY = 1
        self.TIMEOUT = 10
        self.pcode = 0
        return
    
    def create_socket(self, port, protocol):
        self.set_port(port)
        self.set_protocol(protocol)
        return
    
    def split_packet(self):
        data_len, pcode, entity = unpack(">IHH", self.incoming_packet[:8])
        data = self.incoming_packet[8:]
        self.incoming_data_len = data_len
        self.incoming_pcode = pcode
        self.incoming_entity = entity
        self.incoming_data = data
        return
    
    def send(self):
        self.main_socket.connect(self.address)
        self.main_socket.sendall(self.outgoing_packet)
        return
    
    def recieve_data_udp(self, data_len):
        received = self.main_socket.recvfrom(data_len)
        self.incoming_packet = received[0]
        return
    
    def recieve_data_tcp(self, data_len):
        received = self.main_socket.recv(data_len)
        print(received)
        while True:
            received += self.main_socket.recv(data_len)
            if len(received) >= data_len:
                break
            else:
                print(received)
        self.incoming_packet = received
        print(received)
        return
    
    def split_packet(self):
        data_len, pcode, entity = unpack(">IHH", self.incoming_packet[:8])
        data = self.incoming_packet[8:]
        self.incoming_data_len = data_len
        self.incoming_pcode = pcode
        self.incoming_entity = entity
        self.incoming_data = data
        return
    
    def send_phase_a(self):
        packet = Packet()
        data = "Hello World!!!".encode("utf-8")
        packet.add_data(data)
        packet.create_packet()
        packet.create_header(self.pcode, self.ENTITY)
        self.outgoing_packet = packet.get_packet()
        self.send()
        return
    
    def receive_phase_a(self):
        self.recieve_data_udp(1024)
        self.split_packet()
        self.incoming_data = unpack(">IIHH", self.incoming_data)
        self.set_port(self.incoming_data[1])
        self.pcode = self.incoming_data[3]
        print("Recieved Phase A response")
        print(f"Switching to port {self.port}")
        return
    
    def receieve_each_phase_b(self):
        self.main_socket.settimeout(5)
        self.recieve_data_udp(1024)
        self.split_packet()
        self.incoming_data = unpack(">I", self.incoming_data)[0]
        return
    
    def receive_last_phase_b(self):
        self.recieve_data_udp(1024)
        self.split_packet()
        self.incoming_data = unpack(">II", self.incoming_data)
        self.set_port(self.incoming_data[0])
        self.set_protocol("TCP")
        self.pcode = self.incoming_data[1]
        return

    def send_phase_b(self):
        multiple = self.incoming_data[2]
        if multiple % 4 > 0:
            multiple += 4 - (multiple % 4)
        data = b'0' * multiple
        message = 1
        repeat = self.incoming_data[0]
        retry = 0
        print(repeat)
        while message < repeat:
            packet = Packet()
            packet.add_data_format(">I", message)
            packet.add_data(data)
            packet.create_packet()
            packet.create_header(self.pcode, self.ENTITY)
            self.outgoing_packet = packet.get_packet()
            self.send()
            try:
                self.receieve_each_phase_b()
                if self.incoming_data == message:
                    print("Packet Acknowleged!")
                    message += 1
                    retry = 0
            except timeout:
                if retry >= 5:
                    print("Server Unresponsive")
                    print("Exiting...")
                    exit(1)
                else:
                    print("Packet not Acknowleged!")
                    print("Retrying")
                    retry += 1
        self.receive_last_phase_b()
        return
    
    def connect_phase_c(self):
        self.create_socket(self.port, "TCP")
        time.sleep(0.5)
        self.main_socket.connect(self.address)
        self.recieve_data_tcp(21)
        print(self.incoming_packet)
        # self.split_packet()
        # self.incoming_data = unpack(">IIIc", self.incoming_data)
        # self.pcode = self.incoming_data[2]
        # print(self.incoming_data[3])
        return
    
if __name__ == "__main__":
    client = Client(SERVER)
    client.create_socket(INITIAL_PORT, "UDP")
    client.send_phase_a()
    client.receive_phase_a()
    client.send_phase_b()
    client.connect_phase_c()