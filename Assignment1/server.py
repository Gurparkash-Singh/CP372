from struct import pack, unpack
from sys import exit
from socket import SOL_SOCKET, SO_REUSEADDR
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, timeout
from time import sleep, time
from random import randint

SERVER = ""
CLIENT_ENTITY = 1
SERVER_ENTITY = 2
SEP = "=" * 100

class Packet:
    """
        Handles Creation of Packets and Validity of Packet Headers
    """
    def get_packet(self, pcode, entity, data):
        assert type(data) == bytes, "pass in bytes"
        self.pcode = pcode
        self.entity = entity
        self.data = data
        self.data_len = len(self.data) + 8
        self.header = pack(">IHH", self.data_len, self.pcode, self.entity)
        self.packet = self.header + self.data
        return self.packet
    
    def set_packet(self, packet):
        self.packet = packet
        self.header = packet[:8]
        self.data = packet[8:]
        unpacked_header = unpack(">IHH", packet[:8])
        self.data_len = unpacked_header[0]
        self.pcode = unpacked_header[1]
        self.entity = unpacked_header[2]
        return
    
    def check_valid_header(self, expected_pcode, expected_entity):
        valid = True
        if len(self.packet) % 4 != 0:
            valid = False
        if len(self.packet) != self.data_len:
            valid = False
        if self.pcode != expected_pcode:
            valid = False
        if self.entity != expected_entity:
            valid = False
        if not valid:
            exit(-1)
        return
    
    @staticmethod
    def add_padding(data, divisor):
        assert type(data) == bytes, "pass in bytes"
        modulo = len(data) % divisor
        if modulo != 0:
            data += bytes(bytearray(divisor - modulo))
        return data
    
class Server:
    def __init__(self, starting_port, timeout, starting_pcode):
        self.address = (SERVER, starting_port)
        self.entity = SERVER_ENTITY
        self.timeout = timeout
        self.pcode = starting_pcode
        self.packet_to_send = Packet()
        self.recieved_packet = Packet()
        self.complete_all()
        return
    
    def create_socket(self, protocol):
        self.socket = socket(AF_INET, protocol)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(self.address)
        if protocol == SOCK_STREAM:
            self.socket.listen(1)
            self.socket, self.client_address = self.socket.accept()
        self.socket.settimeout(3)
        return
    
    def change_address(self, port):
        self.address = (SERVER, port)
        return
    
    def recieve(self):
        not_connected = True
        while not_connected:
            packet, client_address = self.socket.recvfrom(2048)
            self.recieved_packet.set_packet(packet)
            self.client_address = client_address
            not_connected = False
        return
    
    def verify_phase_a(self):
        self.recieved_packet.check_valid_header(self.pcode, CLIENT_ENTITY)
        data = self.recieved_packet.data
        data = unpack(f">{len(data)}p", data)[0].decode("utf-8")
        if data.strip() != "Hello World!!!":
            exit(-1)
        return data
    
    def send_phase_a(self):
        self.repeat = randint(5, 20)
        self.port = randint(20000, 30000)
        self.recieve_length = randint(50, 100)
        old_pcode = self.pcode
        self.pcode = randint(100, 400)
        data = pack(
            ">IIHH",
            self.repeat,
            self.port,
            self.recieve_length,
            self.pcode
        )
        Packet.add_padding(data, 4)
        packet = self.packet_to_send.get_packet(old_pcode, self.entity, data)
        self.socket.sendto(packet, self.client_address)
        return
    
    def complete_phase_a(self):
        print("Phase A: ")
        self.create_socket(SOCK_DGRAM)
        self.recieve()
        data = self.verify_phase_a()
        self.send_phase_a()
        self.socket.close()
        self.change_address(self.port)
        print(data)
        print(SEP)
        return
    
    def verify_phase_b(self, expected_packet_id):
        self.recieved_packet.check_valid_header(self.pcode, CLIENT_ENTITY)
        data = self.recieved_packet.data
        packet_id = unpack(f">I", self.recieved_packet.data[:4])[0]
        data = self.recieved_packet.data[4:]
        expected_length = self.recieve_length
        if self.recieve_length % 4 != 0:
            expected_length = (4 - (self.recieve_length % 4))
            expected_length += self.recieve_length
        if len(data) != expected_length:
            exit(-1)
        if packet_id > expected_packet_id:
            exit(-1)
        return packet_id
    
    def send_one_phase_b(self, packet_id):
        send_acknowledgement = True if randint(0, 20) > 1 else False
        if send_acknowledgement:
            data = pack(">I", packet_id)
            Packet.add_padding(data, 4)
            packet = self.packet_to_send.get_packet(
                self.pcode,
                self.entity,
                data
            )
            self.socket.sendto(packet, self.client_address)
            packet_id += 1
        return packet_id
    
    def send_ack_all_phase_b(self):
        self.port = randint(20000, 30000)
        old_pcode = self.pcode
        self.pcode = randint(100, 400)
        tcp_port = pack(">I", self.port)
        Packet.add_padding(tcp_port, 4)
        codeB = pack(">I", self.pcode)
        Packet.add_padding(codeB, 4)
        data = tcp_port + codeB
        packet = self.packet_to_send.get_packet(old_pcode, self.entity, data)
        self.socket.sendto(packet, self.client_address)
        return
    
    def complete_phase_b(self):
        print("Phase B: ")
        packet_id = 0
        self.create_socket(SOCK_DGRAM)
        self.socket.settimeout(5)
        while packet_id < self.repeat:
            self.recieve()
            packet_id = self.verify_phase_b(packet_id)
            packet_id = self.send_one_phase_b(packet_id)
            print(f"Recieved Acknowledgement for packet {packet_id - 1}")
        self.send_ack_all_phase_b()
        self.socket.close()
        self.change_address(self.port)
        print(SEP)
        return
    
    def send_phase_c(self):
        self.repeat = randint(5, 20)
        self.recieve_length = randint(50, 100)
        old_pcode = self.pcode
        self.pcode = randint(100, 400)
        char = chr(randint(ord("A"), ord("Z")))
        data = pack(
            ">IIIc",
            self.repeat,
            self.recieve_length,
            self.pcode,
            char.encode("utf-8")
        )
        data = Packet.add_padding(data, 4)
        packet = self.packet_to_send.get_packet(old_pcode, self.entity, data)
        self.socket.send(packet)
        return char
    
    def complete_phase_c(self):
        print("Phase C:")
        self.create_socket(SOCK_STREAM)
        char = self.send_phase_c()
        print(char)
        print(SEP)
        return char
    
    def verify_packet(self, packet, char):
        self.recieved_packet.set_packet(packet)
        self.recieved_packet.check_valid_header(self.pcode, CLIENT_ENTITY)
        data = self.recieved_packet.data
        data = unpack(f">{len(data)}s", data)[0].decode("utf-8")
        expected_length = self.recieve_length
        if self.recieve_length % 4 != 0:
            expected_length = (4 - (self.recieve_length % 4))
            expected_length += self.recieve_length
        if len(data) != expected_length:
            exit(-1)
        for character in data:
            if character != char:
                exit(-1)
        return data

    def send_phase_d(self):
        old_pcode = self.pcode
        self.pcode = randint(100, 400)
        data = pack(">I", self.pcode)
        data = Packet.add_padding(data, 4)
        packet = self.packet_to_send.get_packet(old_pcode, self.entity, data)
        self.socket.send(packet)
        return
    
    def complete_phase_d(self, char):
        packet_id = 0
        print("Phase D:")
        t1 = time()
        packet = self.socket.recv(4)
        data_len = unpack(">I", packet)[0]
        packets = []
        while len(packet) < data_len:
            packet += self.socket.recv(4)
        packets.append(packet)
        data = self.verify_packet(packet, char)
        print(f"Packet {packet_id} recieved")
        print(data)
        while len(packets) < self.repeat:
            packet = b''
            while len(packet) < data_len:
                packet += self.socket.recv(4)
            packets.append(packet)
            packet_id += 1
            data = self.verify_packet(packet, char)
            print(f"Packet {packet_id} recieved")
            print(data)
        self.send_phase_d()
        self.socket.close()
        print(SEP)
        return
    
    def complete_all(self):
        print("Server Running")
        print(SEP)
        self.complete_phase_a()
        self.complete_phase_b()
        char = self.complete_phase_c()
        self.complete_phase_d(char)
        return

def main():
    pcode = 0
    timeout = 3
    port = 12000
    Server(port, timeout, pcode)
    return
    
if __name__ == "__main__":
    main()