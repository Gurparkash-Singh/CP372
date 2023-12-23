from struct import pack, unpack
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, timeout
from server import Packet, SERVER, SERVER_ENTITY, CLIENT_ENTITY, SEP
from time import sleep

class Client:
    def __init__(self, starting_port, starting_pcode):
        self.address = (SERVER, starting_port)
        self.entity = CLIENT_ENTITY
        self.pcode = starting_pcode
        self.packet_to_send = Packet()
        self.recieved_packet = Packet()
        self.complete_all()
        return
    
    def create_socket(self, protocol):
        self.socket = socket(AF_INET, protocol)
        if protocol == SOCK_STREAM:
            self.socket.connect((self.address))
        return
    
    def change_address(self, port):
        self.address = (SERVER, port)
        return
    
    def send_phase_a(self, data):
        data = pack(f">{len(data) + 1}p", data)
        data = Packet.add_padding(data, 4)
        packet = self.packet_to_send.get_packet(self.pcode, self.entity, data)
        self.socket.sendto(packet, self.address)
        return

    def recieve_phase_a(self):
        packet, _ = self.socket.recvfrom(2048)
        self.recieved_packet.set_packet(packet)
        self.recieved_packet.check_valid_header(self.pcode, SERVER_ENTITY)
        data = self.recieved_packet.data
        data = unpack(">IIHH", data)
        self.repeat = data[0]
        self.port = data[1]
        self.data_length = data[2]
        self.pcode = data[3]
        return
    
    def complete_phase_a(self):
        print("Phase A:")
        data = "Hello World!!!".encode("utf-8")
        self.create_socket(SOCK_DGRAM)
        self.send_phase_a(data)
        self.recieve_phase_a()
        self.socket.close()
        self.change_address(self.port)
        print(f"For Phase B send {self.repeat} packets")
        print(f"For Phase B use {self.port} port")
        print(f"For Phase B send data with {self.data_length} bytes")
        print("\tRound to the nearest number divisble by 4")
        print(f"For Phase B use {self.pcode} as the pcode")
        print(SEP)
        return
    
    def send_phase_b(self, packet_id):
        data = pack(">I", packet_id)
        data = Packet.add_padding(data, 4)
        unpadded_data = bytearray(self.data_length)
        data += Packet.add_padding(bytes(unpadded_data), 4)
        packet = self.packet_to_send.get_packet(self.pcode, self.entity, data)
        self.socket.sendto(packet, self.address)
        return
    
    def recieve_one_phase_b(self):
        recieved = True
        data = None
        try:
            packet, _ = self.socket.recvfrom(2048)
            self.recieved_packet.set_packet(packet)
            self.recieved_packet.check_valid_header(self.pcode, SERVER_ENTITY)
            data = self.recieved_packet.data
            data = unpack(">I", data)[0]
        except timeout:
            recieved = False
        return recieved, data
    
    def recieve_ack_all_phase_b(self):
        packet, _ = self.socket.recvfrom(2048)
        self.recieved_packet.set_packet(packet)
        self.recieved_packet.check_valid_header(self.pcode, SERVER_ENTITY)
        data = self.recieved_packet.data
        data = unpack(">II", data)
        self.port = data[0]
        self.pcode = data[1]
        return
    
    def complete_phase_b(self):
        print("Phase B:")
        self.create_socket(SOCK_DGRAM)
        self.socket.settimeout(1)
        for packet_id in range(self.repeat):
            self.send_phase_b(packet_id)
            recieved, data = self.recieve_one_phase_b()
            while not recieved:
                print("Resending Packet")
                self.send_phase_b(packet_id)
                recieved, data = self.recieve_one_phase_b()
            print(f"Recieved Acknowledgement for packet {data}")
        self.recieve_ack_all_phase_b()
        self.socket.close()
        self.change_address(self.port)
        print("\nFrom Phase C onwards use TCP as protocol")
        print(f"For Phase C use {self.port} port")
        print(f"For Phase C use {self.pcode} as the pcode")
        print(SEP)
        return
    
    def recieve_phase_c(self):
        packet, _ = self.socket.recvfrom(2048)
        self.recieved_packet.set_packet(packet)
        self.recieved_packet.check_valid_header(self.pcode, SERVER_ENTITY)
        data = self.recieved_packet.data
        data = unpack(">IIIc", data[:13])
        self.repeat = data[0]
        self.data_length = data[1]
        self.pcode = data[2]
        char = data[3].decode("utf-8")
        return char
    
    def complete_phase_c(self):
        sleep(0.5)
        print("Phase C:")
        self.create_socket(SOCK_STREAM)
        char = self.recieve_phase_c()
        print(f"For Phase D send {self.repeat} packets")
        print(f"For Phase D use {char} as the character to fill data with")
        print(f"For Phase D send data with {self.data_length} bytes")
        print("\tRound to the nearest number divisble by 4")
        print(f"For Phase D use {self.pcode} as the pcode")
        print(SEP)
        return char
    
    def send_phase_d(self, char):
        data = ""
        for _ in range(self.data_length):
            data += char
        data = pack(f">{self.data_length}s", data.encode("utf-8"))
        packet = self.packet_to_send.get_packet(self.pcode, self.entity, data)
        self.socket.send(packet)
        return
    
    def recieve_phase_d(self):
        packet = self.socket.recv(2048)
        self.recieved_packet.set_packet(packet)
        self.recieved_packet.check_valid_header(self.pcode, SERVER_ENTITY)
        data = self.recieved_packet.data
        data = unpack(">I", data)[0]
        return data
    
    def complete_phase_d(self, char):
        print("Phase D:")
        if self.data_length % 4 != 0:
            self.data_length += (4 - (self.data_length % 4))
        for packet_id in range(self.repeat):
            self.send_phase_d(char)
            print(f"Packet {packet_id} Sent")
        data = self.recieve_phase_d()
        self.socket.close()
        print(f"CodeD sent by server is: {data}")
        print(SEP)
        return
    
    def complete_all(self):
        print("Client Started")
        print(SEP)
        self.complete_phase_a()
        self.complete_phase_b()
        char = self.complete_phase_c()
        self.complete_phase_d(char)
        return

def main():
    pcode = 0
    port = 12000
    Client(port, pcode)
    return
    
if __name__ == "__main__":
    main()