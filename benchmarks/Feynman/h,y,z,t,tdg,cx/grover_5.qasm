OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[9];
h qubits[0];
y qubits[0];
z qubits[0];
h qubits[1];
y qubits[1];
z qubits[1];
h qubits[2];
h qubits[3];
h qubits[4];
y qubits[4];
z qubits[4];
y qubits[5];
z qubits[5];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[8];
cx qubits[8],qubits[5];
tdg qubits[5];
cx qubits[4],qubits[5];
t qubits[5];
cx qubits[8],qubits[5];
t qubits[8];
tdg qubits[5];
cx qubits[4],qubits[5];
cx qubits[4],qubits[8];
t qubits[4];
tdg qubits[8];
cx qubits[4],qubits[8];
y qubits[4];
z qubits[4];
t qubits[5];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
y qubits[2];
z qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
h qubits[3];
y qubits[3];
z qubits[3];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[4];
cx qubits[7],qubits[4];
tdg qubits[4];
cx qubits[3],qubits[4];
t qubits[4];
cx qubits[7],qubits[4];
t qubits[7];
tdg qubits[4];
cx qubits[3],qubits[4];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
y qubits[3];
z qubits[3];
t qubits[4];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
y qubits[2];
z qubits[2];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
cx qubits[7],qubits[8];
tdg qubits[8];
h qubits[3];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[8];
cx qubits[8],qubits[5];
tdg qubits[5];
h qubits[4];
y qubits[4];
z qubits[4];
cx qubits[4],qubits[5];
t qubits[5];
cx qubits[8],qubits[5];
t qubits[8];
tdg qubits[5];
cx qubits[4],qubits[5];
cx qubits[4],qubits[8];
t qubits[4];
tdg qubits[8];
cx qubits[4],qubits[8];
y qubits[4];
z qubits[4];
t qubits[5];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
y qubits[2];
z qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
h qubits[3];
y qubits[3];
z qubits[3];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[4];
cx qubits[7],qubits[4];
tdg qubits[4];
cx qubits[3],qubits[4];
t qubits[4];
cx qubits[7],qubits[4];
t qubits[7];
tdg qubits[4];
cx qubits[3],qubits[4];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
y qubits[3];
z qubits[3];
t qubits[4];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
y qubits[2];
z qubits[2];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
cx qubits[7],qubits[8];
tdg qubits[8];
h qubits[3];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[8];
cx qubits[8],qubits[5];
tdg qubits[5];
h qubits[4];
y qubits[4];
z qubits[4];
cx qubits[4],qubits[5];
t qubits[5];
cx qubits[8],qubits[5];
t qubits[8];
tdg qubits[5];
cx qubits[4],qubits[5];
cx qubits[4],qubits[8];
t qubits[4];
tdg qubits[8];
cx qubits[4],qubits[8];
y qubits[4];
z qubits[4];
t qubits[5];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
y qubits[2];
z qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
h qubits[3];
y qubits[3];
z qubits[3];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[4];
cx qubits[7],qubits[4];
tdg qubits[4];
cx qubits[3],qubits[4];
t qubits[4];
cx qubits[7],qubits[4];
t qubits[7];
tdg qubits[4];
cx qubits[3],qubits[4];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
y qubits[3];
z qubits[3];
t qubits[4];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
y qubits[2];
z qubits[2];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
cx qubits[7],qubits[8];
tdg qubits[8];
h qubits[3];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[8];
cx qubits[8],qubits[5];
tdg qubits[5];
h qubits[4];
y qubits[4];
z qubits[4];
cx qubits[4],qubits[5];
t qubits[5];
cx qubits[8],qubits[5];
t qubits[8];
tdg qubits[5];
cx qubits[4],qubits[5];
cx qubits[4],qubits[8];
t qubits[4];
tdg qubits[8];
cx qubits[4],qubits[8];
y qubits[4];
z qubits[4];
t qubits[5];
h qubits[5];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[3],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[3],qubits[8];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[8];
h qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[0];
z qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
y qubits[1];
z qubits[1];
t qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
h qubits[2];
y qubits[2];
z qubits[2];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[7];
h qubits[7];
h qubits[3];
y qubits[3];
z qubits[3];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[4];
cx qubits[7],qubits[4];
tdg qubits[4];
cx qubits[3],qubits[4];
t qubits[4];
cx qubits[7],qubits[4];
t qubits[7];
tdg qubits[4];
cx qubits[3],qubits[4];
cx qubits[3],qubits[7];
t qubits[3];
tdg qubits[7];
cx qubits[3],qubits[7];
y qubits[3];
z qubits[3];
t qubits[4];
h qubits[4];
y qubits[4];
z qubits[4];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[2],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[2],qubits[7];
cx qubits[2],qubits[6];
t qubits[2];
tdg qubits[6];
cx qubits[2],qubits[6];
y qubits[2];
z qubits[2];
t qubits[7];
h qubits[7];
h qubits[6];
cx qubits[1],qubits[6];
tdg qubits[6];
cx qubits[0],qubits[6];
t qubits[6];
cx qubits[1],qubits[6];
t qubits[1];
tdg qubits[6];
cx qubits[0],qubits[6];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
h qubits[0];
y qubits[1];
z qubits[1];
h qubits[1];
t qubits[6];
h qubits[6];
h qubits[2];
h qubits[3];
h qubits[4];
