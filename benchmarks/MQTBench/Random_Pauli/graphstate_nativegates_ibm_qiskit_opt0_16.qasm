OPENQASM 2.0;
include "qelib1.inc";
qreg q[16];
rz(pi/2) q[0];
rx(pi/2) q[0];
rz(pi/2) q[0];
rz(pi/2) q[1];
rx(pi/2) q[1];
rz(pi/2) q[1];
rz(pi/2) q[1];
rx(pi/2) q[1];
rz(pi/2) q[1];
cx q[0],q[1];
rz(pi/2) q[1];
rx(pi/2) q[1];
rz(pi/2) q[1];
rz(pi/2) q[2];
rx(pi/2) q[2];
rz(pi/2) q[2];
rz(pi/2) q[3];
rx(pi/2) q[3];
rz(pi/2) q[3];
rz(pi/2) q[3];
rx(pi/2) q[3];
rz(pi/2) q[3];
cx q[2],q[3];
rz(pi/2) q[3];
rx(pi/2) q[3];
rz(pi/2) q[3];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
cx q[1],q[4];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
cx q[3],q[4];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
rz(pi/2) q[5];
rx(pi/2) q[5];
rz(pi/2) q[5];
rz(pi/2) q[6];
rx(pi/2) q[6];
rz(pi/2) q[6];
rz(pi/2) q[6];
rx(pi/2) q[6];
rz(pi/2) q[6];
cx q[5],q[6];
rz(pi/2) q[6];
rx(pi/2) q[6];
rz(pi/2) q[6];
rz(pi/2) q[7];
rx(pi/2) q[7];
rz(pi/2) q[7];
rz(pi/2) q[8];
rx(pi/2) q[8];
rz(pi/2) q[8];
rz(pi/2) q[8];
rx(pi/2) q[8];
rz(pi/2) q[8];
cx q[7],q[8];
rz(pi/2) q[8];
rx(pi/2) q[8];
rz(pi/2) q[8];
rz(pi/2) q[9];
rx(pi/2) q[9];
rz(pi/2) q[9];
rz(pi/2) q[9];
rx(pi/2) q[9];
rz(pi/2) q[9];
cx q[6],q[9];
rz(pi/2) q[9];
rx(pi/2) q[9];
rz(pi/2) q[9];
rz(pi/2) q[10];
rx(pi/2) q[10];
rz(pi/2) q[10];
rz(pi/2) q[10];
rx(pi/2) q[10];
rz(pi/2) q[10];
cx q[9],q[10];
rz(pi/2) q[10];
rx(pi/2) q[10];
rz(pi/2) q[10];
rz(pi/2) q[11];
rx(pi/2) q[11];
rz(pi/2) q[11];
rz(pi/2) q[11];
rx(pi/2) q[11];
rz(pi/2) q[11];
cx q[7],q[11];
rz(pi/2) q[11];
rx(pi/2) q[11];
rz(pi/2) q[11];
rz(pi/2) q[12];
rx(pi/2) q[12];
rz(pi/2) q[12];
rz(pi/2) q[12];
rx(pi/2) q[12];
rz(pi/2) q[12];
cx q[5],q[12];
rz(pi/2) q[12];
rx(pi/2) q[12];
rz(pi/2) q[12];
rz(pi/2) q[12];
rx(pi/2) q[12];
rz(pi/2) q[12];
cx q[8],q[12];
rz(pi/2) q[12];
rx(pi/2) q[12];
rz(pi/2) q[12];
rz(pi/2) q[13];
rx(pi/2) q[13];
rz(pi/2) q[13];
rz(pi/2) q[13];
rx(pi/2) q[13];
rz(pi/2) q[13];
cx q[10],q[13];
rz(pi/2) q[13];
rx(pi/2) q[13];
rz(pi/2) q[13];
rz(pi/2) q[13];
x q[10];
rx(pi/2) q[13];
rz(pi/2) q[13];
cx q[11],q[13];
rz(pi/2) q[13];
rx(pi/2) q[13];
rz(pi/2) q[13];
rz(pi/2) q[14];
rx(pi/2) q[14];
rz(pi/2) q[14];
rz(pi/2) q[14];
rx(pi/2) q[14];
rz(pi/2) q[14];
cx q[2],q[14];
rz(pi/2) q[14];
rx(pi/2) q[14];
rz(pi/2) q[14];
rz(pi/2) q[15];
rx(pi/2) q[15];
rz(pi/2) q[15];
rz(pi/2) q[15];
rx(pi/2) q[15];
rz(pi/2) q[15];
cx q[0],q[15];
rz(pi/2) q[15];
rx(pi/2) q[15];
rz(pi/2) q[15];
rz(pi/2) q[15];
rx(pi/2) q[15];
rz(pi/2) q[15];
cx q[14],q[15];
rz(pi/2) q[15];
rx(pi/2) q[15];
rz(pi/2) q[15];
