from traceback import print_exc


class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.datagrama = b''
        self.old_byte = b''

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        datagrama = datagrama.replace(b'\xdb', b'\xdb\xdd').replace(
            b'\xc0', b'\xdb\xdc'
        )
        self.linha_serial.enviar(b'\xc0' + datagrama + b'\xc0')

    def __raw_recv(self, dados):
        for data in dados:
            mark = True
            byte = data.to_bytes(1, byteorder='big')

            if self.old_byte + byte == b'\xdb\xdd':
                byte = b'\xdb'
                self.datagrama = self.datagrama[:-1]

            if self.old_byte + byte == b'\xdb\xdc':
                byte = b'\xc0'
                self.datagrama = self.datagrama[:-1]
                self.datagrama += byte
                mark = False

            if byte != b'\xc0':
                self.datagrama += byte

            elif self.datagrama and mark:
                try:
                    self.callback(self.datagrama)
                except:
                    print_exc()

                finally:
                    self.datagrama = b''
                    mark = True

            self.old_byte = byte
