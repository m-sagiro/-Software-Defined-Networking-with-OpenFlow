from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel, info, info, error, debug, output, warn
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.link import TCLink, Intf
from mininet.cli import CLI
from mininet.node import Node
import time, re
import string    
import random # define the random module  

def setup_GRE_Tunnels(net):
    for i in range(1,5):
        for j in range(1,5):
            if i != j:
                gre = "gre%s%s" % (i,j)
                local = "10.10.%s%s.%s" % (j,i,i)
                remote = "10.10.%s%s.%s" % (i,j,j)
                ip = "10.10.%s%s.%s/24" % (j,i,i)

                info(net['r1'].cmd(
                "ip tunnel add "+gre+" mode gre local "+local+" remote "+remote+"  ttl 255"))
                info(net['r1'].cmd("ip link set "+gre+" up"))
                info(net['r1'].cmd("ip addr add "+ip+" dev "+gre))

def generate_key(_key_length):
    ran = ''.join(random.choices(string.ascii_uppercase + string.digits, k = _key_length))    
    return "0x" + str(ran).lower()

def setup_ipsec(net):
    for i in range(1,5):
        for j in range(2,5):
            if(i < j ):
                key_one = generate_key(64)
                key_two = generate_key(64)
                spi_one = generate_key(8)
                spi_two = generate_key(8)
                src = "10.100.%s%s.%s" % (i,j,i)
                dst = "10.100.%s%s.%s" % (i,j,j)

                info(net['r%s'].cmd("ip xfrm state add src "+src+" dst "+dst+" proto esp spi " +
                        spi_one + " enc 'cbc(aes)' " + key_one + " mode transport")) % (i)
                info(net['r%s'].cmd("ip xfrm state add src "+dst+" dst "+src+" proto esp spi " +
                                spi_two + " enc 'cbc(aes)' " + key_two + " mode transport")) % (i)

                info(net['r%s'].cmd("ip xfrm state add src 10.100.12.1 dst 10.100.12.2 proto esp spi " +
                                spi_one + " enc 'cbc(aes)' " + key_one + " mode transport")) % (j)
                info(net['r%s'].cmd("ip xfrm state add src 10.100.12.2 dst 10.100.12.1 proto esp spi " +
                                spi_two + " enc 'cbc(aes)' " + key_two + " mode transport")) % (j)

                info(net['r%s'].cmd(
                    "ip xfrm policy add dir out src "+src+" dst "+dst+" tmpl proto esp mode transport")) % (i)
                info(net['r%s'].cmd(
                    "ip xfrm policy add dir in src "+dst+" dst "+src+" tmpl proto esp mode transport")) % (i)

                info(net['r%s'].cmd(
                    "ip xfrm policy add dir out src "+dst+" dst "+src+" tmpl proto esp mode transport")) % (j)
                info(net['r%s'].cmd(
                    "ip xfrm policy add dir in src "+src+" dst "+dst+" tmpl proto esp mode transport")) % (j)

# Eine Node mit ipv4 forwarding aktiviert
# Dient zur erstellung eines Host's der als Router fungiert
class Router(Node):
    def config(self, **params):
        super(Router, self).config(**params)
        # Enable forwarding on the router
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(Router, self).terminate()

# Hier implementieren wir unseren Netzwerkplan (Topologie)
class Netzwerk(Topo):
    def build(self, n=10, **_opts):

        # IP adresse für die Router r1-r4
        defaultIP = '192.168.%s.1/24'

        # Leere Liste. Gebraucht für später
        routers = []

        # Erstellen der 4 Router, welche jeweils eine Site darstellen
        for r in range(4):
            router = self.addHost(
                'r%s' % (r+1), cls=Router, ip=defaultIP % (r+1), mac='00:00:00:00:00:0%s' % (r+1))
            routers.append(router)

            # Erstellen der 4 Switch's für die vier Sites
            switch = self.addSwitch('s%s' % (r+1))

            # Erstellen der Verlinkung zwischen dem Router und der Switch pro Site
            self.addLink(switch, router, intfName2='r%s-eth1' % (r+1),
                         params2={'ip': defaultIP % (r+1)})

            # Erstellen der 40 Host's (10 pro Site) mit anschließender Verlinkung
            for h in range(n):
                name = ((r)*10)+(h+1)
                host = self.addHost(name='h%s' % (name), ip='192.168.%s.%s/24' % (r+1, h+2),
                                    defaultRoute='via 192.168.%s.1' % (r+1), mac='00:00:00:00:0%s:%s0' % (r+1, h))
                self.addLink(host, switch)

        # Hinzufügen von Interfaces für die Router und Verlinkung der Router untereinander
        # Das stellt unser "Internet" da
        self.addLink(routers[0],
                     routers[1],
                     intfName1='r1-eth2',
                     intfName2='r2-eth2',
                     params1={'ip': '10.100.12.1/24'},
                     params2={'ip': '10.100.12.2/24'},
                     bw=20
                     )
        self.addLink(routers[2],
                     routers[3],
                     intfName1='r3-eth2',
                     intfName2='r4-eth2',
                     params1={'ip': '10.100.34.3/24'},
                     params2={'ip': '10.100.34.4/24'},
                     bw=20
                     )
        self.addLink(routers[0],
                     routers[2],
                     intfName1='r1-eth3',
                     intfName2='r3-eth3',
                     params1={'ip': '10.100.13.1/24'},
                     params2={'ip': '10.100.13.3/24'},
                     bw=20
                     )
        self.addLink(routers[0],
                     routers[3],
                     intfName1='r1-eth4',
                     intfName2='r4-eth3',
                     params1={'ip': '10.100.14.1/24'},
                     params2={'ip': '10.100.14.4/24'},
                     bw=20
                     )
        self.addLink(routers[1],
                     routers[2],
                     intfName1='r2-eth3',
                     intfName2='r3-eth4',
                     params1={'ip': '10.100.23.2/24'},
                     params2={'ip': '10.100.23.3/24'},
                     bw=20
                     )
        self.addLink(routers[1],
                     routers[3],
                     intfName1='r2-eth4',
                     intfName2='r4-eth4',
                     params1={'ip': '10.100.24.2/24'},
                     params2={'ip': '10.100.24.4/24'},
                     bw=20
                     )


# Main-Funktion
def Main():
    # Create our topo object with a function
    topo = Netzwerk()

    # We create our controller and define the properties
    c0 = RemoteController('c0', controller=RemoteController,
                          ip='localhost', port=6653)
    # Initialize a Mininet with our topo object, a controller, the link and switch-version
    net = Mininet(topo=topo, controller=c0,
                  link=TCLink, switch=OVSKernelSwitch)

    # Setting up GRE-Tunnels between the routers
    setup_GRE_Tunnels(net)

    # Add routing for reaching networks that aren't directly connected trough GRE-Tunnel
    # route from r1 to r2 and r2 to r1
    info(net['r1'].cmd("ip route add 192.168.2.0/24 via 10.10.12.2 dev gre12"))
    info(net['r2'].cmd("ip route add 192.168.1.0/24 via 10.10.12.1 dev gre21"))
    # route from r1 to r3 and r3 to r1
    info(net['r1'].cmd("ip route add 192.168.3.0/24 via 10.10.13.1 dev gre13"))
    info(net['r3'].cmd("ip route add 192.168.1.0/24 via 10.10.13.3 dev gre31"))
    # route from r1 to r4 and r4 to r1
    info(net['r1'].cmd("ip route add 192.168.4.0/24 via 10.10.14.1 dev gre14"))
    info(net['r4'].cmd("ip route add 192.168.1.0/24 via 10.10.14.4 dev gre41"))
    # route from r2 to r3 and r3 to r2
    info(net['r2'].cmd("ip route add 192.168.3.0/24 via 10.10.23.2 dev gre23"))
    info(net['r3'].cmd("ip route add 192.168.2.0/24 via 10.10.23.3 dev gre32"))
    # route from r2 to r4 and r4 to r2
    info(net['r2'].cmd("ip route add 192.168.4.0/24 via 10.10.24.2 dev gre24"))
    info(net['r4'].cmd("ip route add 192.168.2.0/24 via 10.10.24.4 dev gre42"))
    # route from r3 to r4 and r4 ro r3
    info(net['r3'].cmd("ip route add 192.168.4.0/24 via 10.10.34.3 dev gre34"))
    info(net['r4'].cmd("ip route add 192.168.3.0/24 via 10.10.34.4 dev gre43"))

    # IPsec-Verbindung
    setup_ipsec(net)

    # Giving routing information output
    info('*** Routing Table on Router:\n')
    info(net['r1'].cmd('route'))
    info(net['r2'].cmd('route'))
    info(net['r3'].cmd('route'))
    info(net['r4'].cmd('route'))

    # Start our mininet
    net.start()

    # Printing informations
    print("Dumping host connections")
    dumpNodeConnections(net.hosts)
    print("Testing network connectivity")

    # Pinging all hosts
    # net.pingAll()

    # Dropping the user in to the CLI -> If Ctrl+c -> stops mininet
    CLI(net)
    # Stopping our mininet simulation
    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    Main()

