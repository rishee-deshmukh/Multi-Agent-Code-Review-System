import os
import socket


def resolve(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def is_host_up(ip):
    output = os.popen(f"ping -c 1 -W 1 {ip}").read()  # @label command_injection critical
    return "1 received" in output


def inventory(hosts):
    return {h: is_host_up(resolve(h) or h) for h in hosts}
