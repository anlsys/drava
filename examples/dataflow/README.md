
### Example run using Sockets
- In terminal 1:
```
socat UNIX-LISTEN:/tmp/accel_2048.sock,fork -
```
- In terminal 2:
```
./examples/example
```
