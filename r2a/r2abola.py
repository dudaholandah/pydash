from player.parser import *
from r2a.ir2a import IR2A
import time
import math


class R2ABola(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.time_request = 0
        self.time = []
        self.throughputs = []

        self.Q = 0
        self.slot = 0
        self.Sm = 0

        self.S = [800, 1000, 1700, 1400, 2000, 3200, 5900, 7500, 5700, 8300, 8600,
                  15000, 22000, 23000, 30000, 38000, 41000, 44000, 45000, 45000]

        '''self.S = [9800, 16000, 24000, 30000, 38000, 45000, 60000, 74000, 89000, 104000, 133000,
                  180000, 226000, 303000, 365000, 443000, 601000, 758000, 898000, 1100000] '''
        self.uM = math.log(self.S[19] / self.S[0])
        self.last_qi = 0
        self.playtime_begin = 0

        u1 = math.log(self.S[19] / self.S[0])
        u2 = math.log(self.S[19] / self.S[1])
        alfa = (self.S[0] * u2 - self.S[1] * u1) / (self.S[1] - self.S[0])
        self.gama_p = (self.uM * 5 - alfa * 60) / (60 - 5)

    def handle_xml_request(self, msg):
        self.time_request = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        t = time.perf_counter() - self.time_request
        self.time.append(0)
        self.throughputs.append((msg.get_bit_length()) / t)
        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        if self.slot == 0:
            msg.add_quality_id(self.qi[0])
            self.last_qi = 0
            self.send_down(msg)

        else:

            buffer = self.whiteboard.get_playback_buffer_size()
            Q = buffer[len(buffer) - 1][1]
            self.playtime_begin = len(self.whiteboard.get_playback_qi())
            t = min(self.playtime_begin, 596 - self.playtime_begin)

            t_linha = max(t / 2, 35)
            Q_maxD = min(60.0, t_linha)
            V_D = (Q_maxD - 1) / (self.uM + self.gama_p)

            ans = 0
            ant = 0
            selected_qi = 0
            for i in range(20):
                self.uM = math.log(self.S[i] / self.S[0])
                q = (V_D * self.uM + V_D * self.gama_p - Q) / self.S[i]
                if q > 0:
                    ans = max(q, ans)
                    if ant != ans:
                        ant = ans
                        selected_qi = i

            if selected_qi > self.last_qi:
                m_linha = 0
                r = self.throughputs[self.slot - 1]
                print(r)
                i = 0
                while self.S[i] <= max(r, self.S[0]) and i < 19:
                    m_linha = i
                    i += 1

                if m_linha >= selected_qi:
                    m_linha = selected_qi
                elif m_linha < self.last_qi:
                    m_linha = self.last_qi
                else:
                    m_linha = m_linha + 1

                selected_qi = m_linha

            self.last_qi = selected_qi
            msg.add_quality_id(self.qi[selected_qi])
            self.time_request = time.perf_counter()
            self.send_down(msg)

    def handle_segment_size_response(self, msg):

        self.slot += 1
        self.Sm = msg.get_bit_length()
        t = time.perf_counter() - self.time_request
        self.time.append(time.perf_counter())
        self.throughputs.append(self.Sm / t)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass