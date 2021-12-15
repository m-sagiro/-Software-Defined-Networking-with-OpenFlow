import http.client
import json
import time

# Firewall wird per PUT request aktiviert
path = '/wm/firewall/module/enable/json'
headers = {'Content-type': 'text/html'}
body = ''
conn = http.client.HTTPConnection('localhost', 8080)
conn.request('PUT', path, body, headers)
response = conn.getresponse()
ret = (response.status, response.reason, response.read())
print(ret)
conn.close()
# Ender der Aktivierung

# Klasse für verschiedene Request-Operationen wie GET, POST und DELETE, um Firewall-Regeln einzutragen


class Firewall(object):
    def get(self):
        ret = self.rest_call({}, 'GET')
        return json.loads(ret[2])

    def set(self, data):
        ret = self.rest_call(data, 'POST')
        return ret[0] == 200

    def remove(self, objtype, data):
        ret = self.rest_call(data, 'DELETE')
        return ret[0] == 200

    def rest_call(self, data, action):
        path = '/wm/firewall/rules/json'
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            }
        body = json.dumps(data)
        conn = http.client.HTTPConnection("localhost", 8080)
        conn.request(action, path, body, headers)
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())
        print(ret)
        conn.close()
        return ret


# Erzeugung unserers Objektes
firewall = Firewall()


# Da wir jetzt die Firewall auf dem Controller eingerichtet haben, müssen wir bestimmte Pakete durchlassen.
# Pakete wären unter anderem PING(ICMP), WWW(HTTP) usw.
# Wäre die Firewall auf dem Router eingerichtet, müssten wir nur ESP durchlassen, da alles verschlüsselt, per "Site-to-Site-VPN", geschickt wird.
# Da die Firewall auf dem Controller ist, müssen wir ganz genau sagen, was wir durchlassen und was nicht.


# VORLAGE = {
#    'switch':"00:00:00:00:00:00:00:01",
#    "src-inport":"",
#    "src-mac":"MAC-ADDRESSE",
#    "dst-mac":"MAC-ADDRESSE",
#    "dl-type":"ARP or IPv4",
#    "src-ip":"IP Bsp.: 192.168.2.1/24..",
#    "dst-ip":"IP Bsp.: 192.168.2.1/24..",
#	 "nw-proto":"TCP or UDP or ICMP",
#	 "tp-src":"",
#    "tp-dst":"",
#	 "priority":"INTEGER",
#	 "action":"ALLOW or DENY. In unserem FALL ALLOW"
#    }

arp_rule = {
    "dl-type": "ARP",
    "src-ip": "192.168.0.0/16",
    "dst-ip": "192.168.0.0/16",
    }

icmp_rule = {
    "src-ip": "192.168.0.0/16",
    "dst-ip": "192.168.0.0/16",
    "nw-proto": "ICMP",
    }

#http_rule = {
#    "src-ip": "192.168.0.0/16",
#    "dst-ip": "192.168.0.0/16",
#    "nw-proto": "TCP",
#    "tp-src": "80",
#    "tp-dst": "80",
#    "action": "ALLOW",
#    }

#https_rule = {
#    "src-ip": "192.168.0.0/16",
#    "dst-ip": "192.168.0.0/16",
#    "nw-proto": "TCP",
#    "tp-src": "443",
#    "tp-dst": "443",
#    }


# site1_arp = {
#    "dl-type":"ARP",
#    "src-ip":"192.168.1.1/24",
#    "dst-ip":"192.168.1.1/24",
#    }

# site1_icmp = {
#    "src-ip":"192.168.1.1/24",
#    "dst-ip":"192.168.1.1/24",
#    "nw-proto":"ICMP",
#    }
#
# site2_arp = {
#    "dl-type":"ARP",
#    "src-ip":"192.168.2.1/24",
#    "dst-ip":"192.168.2.1/24",
#    }

# site2_icmp = {
#    "src-ip":"192.168.2.1/24",
#    "dst-ip":"192.168.2.1/24",
#    "nw-proto":"ICMP",
#    }


# regel2 = {
#    'switch':"00:00:00:00:00:00:00:01",
#    "src-inport":"",
#    "src-mac":"MAC-ADDRESSE",
#    "dst-mac":"MAC-ADDRESSE",
#    "dl-type":"ARP or IPv4",
#    "src-ip":"IP Bsp.: 192.168.2.1/24..",
#    "dst-ip":"IP Bsp.: 192.168.2.1/24..",
#	 "nw-proto":"TCP or UDP or ICMP",
#	 "tp-src":"",
#    "tp-dst":"",
#	 "priority":"INTEGER",
#	 "action":"ALLOW or DENY. In unserem FALL ALLOW"
#    }
#
# regel3 = {
#    'switch':"00:00:00:00:00:00:00:01",
#    "src-inport":"",
#    "src-mac":"MAC-ADDRESSE",
#    "dst-mac":"MAC-ADDRESSE",
#    "dl-type":"ARP or IPv4",
#    "src-ip":"IP Bsp.: 192.168.2.1/24..",
#    "dst-ip":"IP Bsp.: 192.168.2.1/24..",
#	 "nw-proto":"TCP or UDP or ICMP",
#	 "tp-src":"",
#    "tp-dst":"",
#	 "priority":"INTEGER",
#	 "action":"ALLOW or DENY. In unserem FALL ALLOW"
#    }

# regel4 = {
#    'switch':"00:00:00:00:00:00:00:01",
#    "src-inport":"",
#    "src-mac":"MAC-ADDRESSE",
#    "dst-mac":"MAC-ADDRESSE",
#    "dl-type":"ARP or IPv4",
#    "src-ip":"IP Bsp.: 192.168.2.1/24..",
#    "dst-ip":"IP Bsp.: 192.168.2.1/24..",
#	 "nw-proto":"TCP or UDP or ICMP",
#	 "tp-src":"",
#    "tp-dst":"",
#	 "priority":"INTEGER",
#	 "action":"ALLOW or DENY. In unserem FALL ALLOW"
#    }


# Regeln werden nacheinander per POST requestet und im Controller eingetragen.
firewall.set(arp_rule)
firewall.set(icmp_rule)
#firewall.set(http_rule)
#firewall.set(https_rule)

# Abfrage der aktuellen Regeln
# Alle Regeln werden hier gelistet
#firewall.get()
