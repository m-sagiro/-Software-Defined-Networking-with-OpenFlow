from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel, info, info, error, debug, output, warn
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.link import TCLink, Intf
from mininet.cli import CLI
from mininet.node import Node
import time, re

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
        
def customIperf( self=Mininet, hosts=None, l4Type='TCP', udpBw='10M', fmt=None,
               seconds=5, port=5001, args=None):
        """Run iperf between two hosts.
           hosts: list of hosts; if None, uses first and last hosts
           l4Type: string, one of [ TCP, UDP ]
           udpBw: bandwidth target for UDP test
           fmt: iperf format argument if any
           seconds: iperf time to transmit
           port: iperf port
           returns: two-element array of [ server, client ] speeds
           note: send() is buffered, so client rate can be much higher than
           the actual transmission rate; on an unloaded system, server
           rate should be much closer to the actual receive rate"""
        hosts = hosts or [ self.hosts[ 0 ], self.hosts[ -1 ] ]
        assert len( hosts ) == 2
        client, server = hosts
        output( '*** Iperf: testing', l4Type, 'bandwidth between',
                client, 'and', server, '\n' )
        server.cmd( 'killall -9 iperf' )
        iperfArgs = 'iperf -p %d ' % port
        bwArgs = ''
        args = ''
        if l4Type == 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
            args = '-l 1k'
        elif l4Type != 'TCP':
            raise Exception( 'Unexpected l4 type: %s' % l4Type )
        if fmt:
            iperfArgs += '-f %s ' % fmt
        server.sendCmd( iperfArgs + '-s' )
        if l4Type == 'TCP':
            if not waitListening( client, server.IP(), port ):
                raise Exception( 'Could not connect to iperf on port %d'
                                 % port )
        print(iperfArgs + '-t %d -c ' % seconds +
                             server.IP() + ' ' + bwArgs + args)
        cliout = client.cmd( iperfArgs + '-t %d -c ' % seconds +
                             server.IP() + ' ' + bwArgs + args)
        debug( 'Client output: %s\n' % cliout )
        servout = ''
        # We want the last *b/sec from the iperf server output
        # for TCP, there are two of them because of waitListening
        count = 2 if l4Type == 'TCP' else 1
        while len( re.findall( '/sec', servout ) ) < count:
            servout += server.monitor( timeoutms=5000 )
        server.sendInt()
        servout += server.waitOutput()
        debug( 'Server output: %s\n' % servout )
        output(servout)
        result = [ self._parseIperf( servout ), self._parseIperf( cliout ) ]
        if l4Type == 'UDP':
            result.insert( 0, udpBw )
        output( '*** Results: %s\n' % result )
        return result


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
                     #bw=20
                     )
        self.addLink(routers[2],
                     routers[3],
                     intfName1='r3-eth2',
                     intfName2='r4-eth2',
                     params1={'ip': '10.100.34.3/24'},
                     params2={'ip': '10.100.34.4/24'},
                     #bw=20
                     )
        self.addLink(routers[0],
                     routers[2],
                     intfName1='r1-eth3',
                     intfName2='r3-eth3',
                     params1={'ip': '10.100.13.1/24'},
                     params2={'ip': '10.100.13.3/24'},
                     #bw=20
                     )
        self.addLink(routers[0],
                     routers[3],
                     intfName1='r1-eth4',
                     intfName2='r4-eth3',
                     params1={'ip': '10.100.14.1/24'},
                     params2={'ip': '10.100.14.4/24'},
                     #bw=20
                     )
        self.addLink(routers[1],
                     routers[2],
                     intfName1='r2-eth3',
                     intfName2='r3-eth4',
                     params1={'ip': '10.100.23.2/24'},
                     params2={'ip': '10.100.23.3/24'},
                     #bw=20
                     )
        self.addLink(routers[1],
                     routers[3],
                     intfName1='r2-eth4',
                     intfName2='r4-eth4',
                     params1={'ip': '10.100.24.2/24'},
                     params2={'ip': '10.100.24.4/24'},
                     #bw=20
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
    # link und switch können spezifisch eingestellt werden
    #link=TCLink, switch=OVSKernelSwitch
    

    # Creating our Mininet Object with our created Netzwerk (topology)
    #net = Mininet(topo=topo)

    # Setting up GRE-Tunnels between the routers
    info(net['r1'].cmd(
        "ip tunnel add gre12 mode gre local 10.100.12.1 remote 10.100.12.2 ttl 255"))
    info(net['r1'].cmd("ip link set gre12 up"))
    info(net['r1'].cmd("ip addr add 10.10.12.1/24 dev gre12"))

    info(net['r1'].cmd(
        "ip tunnel add gre13 mode gre local 10.100.13.1 remote 10.100.13.3 ttl 255"))
    info(net['r1'].cmd("ip link set gre13 up"))
    info(net['r1'].cmd("ip addr add 10.10.13.1/24 dev gre13"))

    info(net['r1'].cmd(
        "ip tunnel add gre14 mode gre local 10.100.14.1 remote 10.100.14.4 ttl 255"))
    info(net['r1'].cmd("ip link set gre14 up"))
    info(net['r1'].cmd("ip addr add 10.10.14.1/24 dev gre14"))

    info(net['r2'].cmd(
        "ip tunnel add gre21 mode gre local 10.100.12.2 remote 10.100.12.1 ttl 255"))
    info(net['r2'].cmd("ip link set gre21 up"))
    info(net['r2'].cmd("ip addr add 10.10.12.2/24 dev gre21"))

    info(net['r2'].cmd(
        "ip tunnel add gre23 mode gre local 10.100.23.2 remote 10.100.23.3 ttl 255"))
    info(net['r2'].cmd("ip link set gre23 up"))
    info(net['r2'].cmd("ip addr add 10.10.23.2/24 dev gre23"))

    info(net['r2'].cmd(
        "ip tunnel add gre24 mode gre local 10.100.24.2 remote 10.100.24.4 ttl 255"))
    info(net['r2'].cmd("ip link set gre24 up"))
    info(net['r2'].cmd("ip addr add 10.10.24.2/24 dev gre24"))

    info(net['r3'].cmd(
        "ip tunnel add gre31 mode gre local 10.100.13.3 remote 10.100.13.1 ttl 255"))
    info(net['r3'].cmd("ip link set gre31 up"))
    info(net['r3'].cmd("ip addr add 10.10.13.3/24 dev gre31"))

    info(net['r3'].cmd(
        "ip tunnel add gre32 mode gre local 10.100.23.3 remote 10.100.23.2 ttl 255"))
    info(net['r3'].cmd("ip link set gre32 up"))
    info(net['r3'].cmd("ip addr add 10.10.23.3/24 dev gre32"))

    info(net['r3'].cmd(
        "ip tunnel add gre34 mode gre local 10.100.34.3 remote 10.100.34.4 ttl 255"))
    info(net['r3'].cmd("ip link set gre34 up"))
    info(net['r3'].cmd("ip addr add 10.10.34.3/24 dev gre34"))

    info(net['r4'].cmd(
        "ip tunnel add gre41 mode gre local 10.100.14.4 remote 10.100.14.1 ttl 255"))
    info(net['r4'].cmd("ip link set gre41 up"))
    info(net['r4'].cmd("ip addr add 10.10.14.4/24 dev gre41"))

    info(net['r4'].cmd(
        "ip tunnel add gre42 mode gre local 10.100.24.4 remote 10.100.24.2 ttl 255"))
    info(net['r4'].cmd("ip link set gre42 up"))
    info(net['r4'].cmd("ip addr add 10.10.24.4/24 dev gre42"))

    info(net['r4'].cmd(
        "ip tunnel add gre43 mode gre local 10.100.34.4 remote 10.100.34.3 ttl 255"))
    info(net['r4'].cmd("ip link set gre43 up"))
    info(net['r4'].cmd("ip addr add 10.10.34.4/24 dev gre43"))

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

    # Random's für die IPsec-Verbindung
    key12 = "0xf1e125c62a8f68169ff9d0375d9017b76c700354e3060ef78a61e43547babd0d"
    key21 = "0xc9d786b186394addc49c08fc551cd5cf580f7cd600da9ed5c47d1ab7b7e510ec"
    spi12 = "0x1cac64a1"
    spi21 = "0xd03e561e"

    # Setting up ipsec in Transport mode
    info(net['r1'].cmd("ip xfrm state add src 10.100.12.1 dst 10.100.12.2 proto esp spi " +
                       spi12 + " enc 'cbc(aes)' " + key12 + " mode transport"))
    info(net['r1'].cmd("ip xfrm state add src 10.100.12.2 dst 10.100.12.1 proto esp spi " +
                       spi21 + " enc 'cbc(aes)' " + key21 + " mode transport"))

    info(net['r2'].cmd("ip xfrm state add src 10.100.12.1 dst 10.100.12.2 proto esp spi " +
                       spi12 + " enc 'cbc(aes)' " + key12 + " mode transport"))
    info(net['r2'].cmd("ip xfrm state add src 10.100.12.2 dst 10.100.12.1 proto esp spi " +
                       spi21 + " enc 'cbc(aes)' " + key21 + " mode transport"))

    info(net['r1'].cmd(
        "ip xfrm policy add dir out src 10.100.12.1 dst 10.100.12.2 tmpl proto esp mode transport"))
    info(net['r1'].cmd(
        "ip xfrm policy add dir in src 10.100.12.2 dst 10.100.12.1 tmpl proto esp mode transport"))

    info(net['r2'].cmd(
        "ip xfrm policy add dir out src 10.100.12.2 dst 10.100.12.1 tmpl proto esp mode transport"))
    info(net['r2'].cmd(
        "ip xfrm policy add dir in src 10.100.12.1 dst 10.100.12.2 tmpl proto esp mode transport"))

    key13 = "0x66bb7cc6569bd163f9bc08b18e2c713d5bb9e907e19ca5fec3e912ded56d4f3f"
    key31 = "0x7859f3b5ec4fc371d0f39ae07c3036e8fd604ba1da981ed6f369e8eb09883725"
    spi13 = "0x689ba869"
    spi31 = "0x0f054cf0"

    info(net['r1'].cmd("ip xfrm state add src 10.100.13.1 dst 10.100.13.3 proto esp spi " +
                       spi13 + " enc 'cbc(aes)' " + key13 + " mode transport"))
    info(net['r1'].cmd("ip xfrm state add src 10.100.13.3 dst 10.100.13.1 proto esp spi " +
                       spi31 + " enc 'cbc(aes)' " + key31 + " mode transport"))

    info(net['r3'].cmd("ip xfrm state add src 10.100.13.1 dst 10.100.13.3 proto esp spi " +
                       spi13 + " enc 'cbc(aes)' " + key13 + " mode transport"))
    info(net['r3'].cmd("ip xfrm state add src 10.100.13.3 dst 10.100.13.1 proto esp spi " +
                       spi31 + " enc 'cbc(aes)' " + key31 + " mode transport"))

    info(net['r1'].cmd(
        "ip xfrm policy add dir out src 10.100.13.1 dst 10.100.13.3 tmpl proto esp mode transport"))
    info(net['r1'].cmd(
        "ip xfrm policy add dir in src 10.100.13.3 dst 10.100.13.1 tmpl proto esp mode transport"))

    info(net['r3'].cmd(
        "ip xfrm policy add dir out src 10.100.13.3 dst 10.100.13.1 tmpl proto esp mode transport"))
    info(net['r3'].cmd(
        "ip xfrm policy add dir in src 10.100.13.1 dst 10.100.13.3 tmpl proto esp mode transport"))

    key14 = "0x8527ef297dc35bed418d635ef15e219feaf5f5597699b6271534697bfdf940c9"
    key41 = "0x69091e7f7c1c162c7c6b44fb8e389e113eb77746c1d6a2d73074e9609a991179"
    spi14 = "0x19de2473"
    spi41 = "0x65cb9866"

    info(net['r1'].cmd("ip xfrm state add src 10.100.14.1 dst 10.100.14.4 proto esp spi " +
                       spi14 + " enc 'cbc(aes)' " + key14 + " mode transport"))
    info(net['r1'].cmd("ip xfrm state add src 10.100.14.4 dst 10.100.14.1 proto esp spi " +
                       spi41 + " enc 'cbc(aes)' " + key41 + " mode transport"))

    info(net['r4'].cmd("ip xfrm state add src 10.100.14.1 dst 10.100.14.4 proto esp spi " +
                       spi14 + " enc 'cbc(aes)' " + key14 + " mode transport"))
    info(net['r4'].cmd("ip xfrm state add src 10.100.14.4 dst 10.100.14.1 proto esp spi " +
                       spi41 + " enc 'cbc(aes)' " + key41 + " mode transport"))

    info(net['r1'].cmd(
        "ip xfrm policy add dir out src 10.100.14.1 dst 10.100.14.4 tmpl proto esp mode transport"))
    info(net['r1'].cmd(
        "ip xfrm policy add dir in src 10.100.14.4 dst 10.100.14.1 tmpl proto esp mode transport"))

    info(net['r4'].cmd(
        "ip xfrm policy add dir out src 10.100.14.4 dst 10.100.14.1 tmpl proto esp mode transport"))
    info(net['r4'].cmd(
        "ip xfrm policy add dir in src 10.100.14.1 dst 10.100.14.4 tmpl proto esp mode transport"))

    key23 = "0xe6709e851cc4f247729bb592147663ab4e4fe26cced514120e92aaf3034061f8"
    key32 = "0xc765d3e9382d7012963fc2c0d66e20724ba2de74928e6c9f08c0250d6ac5f823"
    spi23 = "0x18d7e3e4"
    spi32 = "0x93e5489f"

    info(net['r2'].cmd("ip xfrm state add src 10.100.23.2 dst 10.100.23.3 proto esp spi " +
                       spi23 + " enc 'cbc(aes)' " + key23 + " mode transport"))
    info(net['r2'].cmd("ip xfrm state add src 10.100.23.3 dst 10.100.23.2 proto esp spi " +
                       spi32 + " enc 'cbc(aes)' " + key32 + " mode transport"))

    info(net['r3'].cmd("ip xfrm state add src 10.100.23.2 dst 10.100.23.3 proto esp spi " +
                       spi23 + " enc 'cbc(aes)' " + key23 + " mode transport"))
    info(net['r3'].cmd("ip xfrm state add src 10.100.23.3 dst 10.100.23.2 proto esp spi " +
                       spi32 + " enc 'cbc(aes)' " + key32 + " mode transport"))

    info(net['r2'].cmd(
        "ip xfrm policy add dir out src 10.100.23.2 dst 10.100.23.3 tmpl proto esp mode transport"))
    info(net['r2'].cmd(
        "ip xfrm policy add dir in src 10.100.23.3 dst 10.100.23.2 tmpl proto esp mode transport"))

    info(net['r3'].cmd(
        "ip xfrm policy add dir out src 10.100.23.3 dst 10.100.23.2 tmpl proto esp mode transport"))
    info(net['r3'].cmd(
        "ip xfrm policy add dir in src 10.100.23.2 dst 10.100.23.3 tmpl proto esp mode transport"))

    key24 = "0xd2851d694a952d4e14b1eda4ee2004e94f601e7422e47c1872ad6d333b7e1d37"
    key42 = "0xcb7698938b9393686afde8b29e2c1e620b99f1fe2435c24709a9ffccfea050f6"
    spi24 = "0x7d99d7e8"
    spi42 = "0x508ef1f2"

    info(net['r2'].cmd("ip xfrm state add src 10.100.24.2 dst 10.100.24.4 proto esp spi " +
                       spi24 + " enc 'cbc(aes)' " + key24 + " mode transport"))
    info(net['r2'].cmd("ip xfrm state add src 10.100.24.4 dst 10.100.24.2 proto esp spi " +
                       spi42 + " enc 'cbc(aes)' " + key42 + " mode transport"))

    info(net['r4'].cmd("ip xfrm state add src 10.100.24.2 dst 10.100.24.4 proto esp spi " +
                       spi24 + " enc 'cbc(aes)' " + key24 + " mode transport"))
    info(net['r4'].cmd("ip xfrm state add src 10.100.24.4 dst 10.100.24.2 proto esp spi " +
                       spi42 + " enc 'cbc(aes)' " + key42 + " mode transport"))

    info(net['r2'].cmd(
        "ip xfrm policy add dir out src 10.100.24.2 dst 10.100.24.4 tmpl proto esp mode transport"))
    info(net['r2'].cmd(
        "ip xfrm policy add dir in src 10.100.24.4 dst 10.100.24.2 tmpl proto esp mode transport"))

    info(net['r4'].cmd(
        "ip xfrm policy add dir out src 10.100.24.4 dst 10.100.24.2 tmpl proto esp mode transport"))
    info(net['r4'].cmd(
        "ip xfrm policy add dir in src 10.100.24.2 dst 10.100.24.4 tmpl proto esp mode transport"))

    key34 = "0xa5036e96c1ee40de3cb7ebc6a455fa816053b6106a352634da87e67b1137c058"
    key43 = "0x4e2ea7cb3ec6d11704d2a85b7f7db3518ddcf970ff54502ff8ea6be653c6b456"
    spi34 = "0x7302a4a9"
    spi43 = "0xc70a7221"

    info(net['r3'].cmd("ip xfrm state add src 10.100.34.3 dst 10.100.34.4 proto esp spi " +
                       spi34 + " enc 'cbc(aes)' " + key34 + " mode transport"))
    info(net['r3'].cmd("ip xfrm state add src 10.100.34.4 dst 10.100.34.3 proto esp spi " +
                       spi43 + " enc 'cbc(aes)' " + key43 + " mode transport"))

    info(net['r4'].cmd("ip xfrm state add src 10.100.34.3 dst 10.100.34.4 proto esp spi " +
                       spi34 + " enc 'cbc(aes)' " + key34 + " mode transport"))
    info(net['r4'].cmd("ip xfrm state add src 10.100.34.4 dst 10.100.34.3 proto esp spi " +
                       spi43 + " enc 'cbc(aes)' " + key43 + " mode transport"))

    info(net['r3'].cmd(
        "ip xfrm policy add dir out src 10.100.34.3 dst 10.100.34.4 tmpl proto esp mode transport"))
    info(net['r3'].cmd(
        "ip xfrm policy add dir in src 10.100.34.4 dst 10.100.34.3 tmpl proto esp mode transport"))

    info(net['r4'].cmd(
        "ip xfrm policy add dir out src 10.100.34.4 dst 10.100.34.3 tmpl proto esp mode transport"))
    info(net['r4'].cmd(
        "ip xfrm policy add dir in src 10.100.34.3 dst 10.100.34.4 tmpl proto esp mode transport"))

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
    
    #hosts = [net.getNodeByName('h1'), net.getNodeByName('h11')]
    
    #info(net['h1'].cmd('wireshark&'))
    #time.sleep(10)
    
    #net.iperf(hosts=hosts, l4Type='TCP')
    
    #customIperf(self=net, hosts=hosts, l4Type='UDP', udpBw='20M', seconds=10)

    # Dropping the user in to the CLI -> If Ctrl+c -> stops mininet
    CLI(net)
    # Stopping our mininet simulation
    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    Main()
