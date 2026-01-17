This project implements a peer-to-peer, bidirectional file synchronization system using TCP sockets in Python. 

Each peer runs a multithreaded service that concurrently monitors local file system changes and listens for remote updates, synchronizing create, update, and delete operations between two directories. 

File content hashing is used to detect real modifications and prevent redundant transfers, ensuring consistency between both folders.
