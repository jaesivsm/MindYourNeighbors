MindYourNeighbors
=================

Launching scripts depending on you direct neighbors


How ?
-----

MindYourNeighbors basically parse the ARP (for IPv4) and neighbour (for IPv6) table through the result of the *ip neigh* command.
If results are found that are not excluded by the configuration, a configured command will be launched (unless already launched).


Why ?
-----

The original use case :

A linux box used as a router as well as a home server. On this box runs several pieces of software which can be very bandwith consuming (ie: transmission).
I wanted to shut down this software when other users were using the network.
