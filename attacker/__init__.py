"""An AI plays the intruder against the demo portal, so judges watch SentrAI catch it.

A local model is handed a few tools, each of which can only touch the fake Aegis portal on this
machine (attacker/tools.py). The model decides what to try; every request still carries a made-up
attacker address and hits nothing but 127.0.0.1:5000. Nothing is ever run on the computer and no
real system is reached, so an "unrestricted" local model is safe to point at it.
"""
