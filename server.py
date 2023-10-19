from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
from socket import SOL_SOCKET, SO_REUSEADDR, timeout
from struct import pack, unpack
from random import randint
from sys import exit
import time

SERVER = "127.0.0.1"
INITIAL_PORT = 12000
HEADER_LENGTH = 8

class Packet:
    def __init__(self):
        self.data = []
        return
    
    def add_data_format(self, format, data):
        self.data.append(pack(format, data))
        return
    
    def add_data(self, data):
        data = bytearray(data)
        if (len(data) % 4) > 0:
            data += b' ' * (4 - (len(data) % 4))
        self.data.append(data)
        return
    
    def create_packet(self):
        self.packet = b''
        for data in self.data:
            self.packet += data
        return len(self.packet)
    
    def create_header(self, pcode, entity):
        self.header = pack(">IHH", len(self.packet), pcode, entity)
        self.packet = self.header + self.packet
        return
    
    def get_packet(self):
        return self.packet

class Socket:
    def __init__(self, server):
        self.SERVER = server
        self.main_socket = None
        return
    
    def _set_address(self):
        self.address = (self.SERVER, self.port)
        return
    
    def _create_socket(self):
        if self.main_socket:
            self.main_socket.close()
        if self.protocol == "TCP":
            self.main_socket = socket(AF_INET, SOCK_STREAM)
        else:
            self.main_socket = socket(AF_INET, SOCK_DGRAM)
        return
    
    def set_port(self, port):
        self.port = port
        self._set_address()
        return
    
    def set_protocol(self, protocol):
        self.protocol = protocol
        self._create_socket()
        return

class Server(Socket):
    def __init__(self, server):
        super().__init__(server)
        self.ENTITY = 2
        self.CLIENT_ENTITY = 1
        self.TIMEOUT = 3
        self.pcode = 0
        return
    
    def create_socket(self, port, protocol):
        self.set_port(port)
        self.set_protocol(protocol)
        self.main_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.main_socket.bind(self.address)
        self.main_socket.settimeout(self.TIMEOUT)
        return
    
    def recieve_packet(self, data_len):
        try:
            received, address = self.main_socket.recvfrom(data_len)
            self.incoming_packet = received
            self.outgoing_address = address
        except timeout:
            print("Socket Timed out!")
            self.main_socket.close()
            exit(1)
        return
    
    def split_packet(self):
        data_len, pcode, entity = unpack(">IHH", self.incoming_packet[:8])
        data = self.incoming_packet[8:]
        self.incoming_data_len = data_len
        self.incoming_pcode = pcode
        self.incoming_entity = entity
        self.incoming_data = data
        return
    
    def validate_header(self):
        self.split_packet()
        if (len(self.incoming_data) % 4) != 0:
            self.main_socket.close()
            print("Invalid Packet Length")
        elif self.incoming_data_len != len(self.incoming_data):
            print("Data Length does not match")
        elif self.incoming_pcode != self.pcode:
            print("Incorrect pcode")
        elif self.incoming_entity != self.CLIENT_ENTITY:
            print("Entity code is incorrect")
        return
    
    def send_packet(self):
        self.main_socket.sendto(self.outgoing_packet, self.outgoing_address)
        return
    
    def receive_phase_a(self):
        self.create_socket(INITIAL_PORT, "UDP")
        self.recieve_packet(1024)
        self.validate_header()
        self.incoming_data = self.incoming_data.decode('utf-8')
        print(self.incoming_data)
        return
    
    def send_phase_a(self):
        packet = Packet()
        repeat = randint(5, 20)
        udp_port = randint(20000, 30000)
        length = randint(50, 100)
        codeA = randint(100, 400)
        packet.add_data_format(">I", repeat)
        packet.add_data_format(">I", udp_port)
        packet.add_data_format(">H", length)
        packet.add_data_format(">H", codeA)
        packet.create_packet()
        packet.create_header(self.pcode, self.ENTITY)
        self.outgoing_packet = packet.get_packet()
        self.pcode = codeA
        self.repeat = repeat
        self.send_packet()
        print(f"Switching ports to {udp_port}")
        self.set_port(udp_port)
        return length
    
    def send_acknowlegment_phase_b(self, repeat):
        packet = Packet()
        packet.add_data_format(">I", repeat)
        packet.create_packet()
        packet.create_header(self.pcode, self.ENTITY)
        self.outgoing_packet = packet.get_packet()
        self.send_packet()
        return True
    
    def acknowledge_all_phase_b(self):
        packet = Packet()
        tcp_port = randint(20000, 30000)
        codeB = randint(100, 400)
        packet.add_data_format(">I", tcp_port)
        packet.add_data_format(">I", codeB)
        packet.create_packet()
        packet.create_header(self.pcode, self.ENTITY)
        self.outgoing_packet = packet.get_packet()
        self.send_packet()
        self.pcode = codeB
        self.set_port(tcp_port)
        self.set_protocol("TCP")
        print(f"Switching to port {self.port} on TCP")
        return
    
    def receive_each_phase_b(self, length):
        self.create_socket(self.port, "UDP")
        self.recieve_packet(1024)
        self.validate_header()
        if len(self.incoming_data) != length:
            print(f"Actual: {len(self.incoming_data)} Expected: {length}")
            print("Length of data does not match")
            self.main_socket.close()
            exit(1)
        print(self.incoming_data)
        return
    
    def receive_all_phase_b(self, length):
        repeat = 1
        print(self.repeat)
        while repeat < self.repeat:
            self.receive_each_phase_b(length)
            packet_id = unpack(">I", self.incoming_data[:4])[0]
            if repeat != packet_id:
                print("Packet Id is incorrect")
                print(f"Expected: {repeat} Actual: {packet_id}")
                self.main_socket.close()
                exit(1)
            success = self.send_acknowlegment_phase_b(repeat)
            if success:
                repeat += 1
        print("Received all packages")
        self.acknowledge_all_phase_b()
        return
    
    def send_phase_c(self):
        self.create_socket(self.port, "TCP")
        self.main_socket.listen()
        conn, addr = self.main_socket.accept()
        repeat = randint(5, 20)
        length = randint(50, 100)
        codeC = randint(100, 400)
        data = bytes("G", "utf-8")
        packet = Packet()
        packet.add_data_format(">I", repeat)
        packet.add_data_format(">I", length)
        packet.add_data_format(">I", codeC)
        packet.add_data_format(">c", data)
        packet.create_packet()
        packet.create_header(self.pcode, self.ENTITY)
        self.outgoing_packet = packet.get_packet()
        self.outgoing_address = addr
        print(len(self.outgoing_packet))
        self.main_socket.sendall("Hello, World!".encode("utf-8"))
        print("Message Sent!")
        self.main_socket.close()
        return
    


if __name__ == "__main__":
    server = Server(SERVER)
    server.receive_phase_a()
    length = server.send_phase_a()
    if length % 4 > 0:
        length += 4 - (length % 4)
    length += 4
    server.receive_all_phase_b(length)
    server.send_phase_c()

    

    
