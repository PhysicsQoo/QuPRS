OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[9];
h qubits[8];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[4],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[4],qubits[8];
cx qubits[4],qubits[7];
t qubits[4];
tdg qubits[7];
cx qubits[4],qubits[7];
t qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[3],qubits[7];
cx qubits[3],qubits[6];
t qubits[3];
tdg qubits[6];
cx qubits[3],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[5],qubits[6];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[6];
cx qubits[5],qubits[6];
t qubits[5];
tdg qubits[6];
cx qubits[2],qubits[6];
cx qubits[2],qubits[5];
t qubits[2];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[6];
h qubits[5];
cx qubits[1],qubits[5];
tdg qubits[5];
cx qubits[0],qubits[5];
t qubits[5];
cx qubits[1],qubits[5];
t qubits[1];
tdg qubits[5];
cx qubits[0],qubits[5];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[5];
h qubits[5];
cx qubits[5],qubits[6];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[6];
cx qubits[5],qubits[6];
t qubits[5];
tdg qubits[6];
cx qubits[2],qubits[6];
cx qubits[2],qubits[5];
t qubits[2];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[3],qubits[7];
cx qubits[3],qubits[6];
t qubits[3];
tdg qubits[6];
cx qubits[3],qubits[6];
t qubits[7];
h qubits[7];
cx qubits[7],qubits[8];
tdg qubits[8];
cx qubits[4],qubits[8];
t qubits[8];
cx qubits[7],qubits[8];
t qubits[7];
tdg qubits[8];
cx qubits[4],qubits[8];
cx qubits[4],qubits[7];
t qubits[4];
tdg qubits[7];
cx qubits[4],qubits[7];
t qubits[8];
h qubits[8];
h qubits[7];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[3],qubits[7];
cx qubits[3],qubits[6];
t qubits[3];
tdg qubits[6];
cx qubits[3],qubits[6];
t qubits[7];
h qubits[6];
cx qubits[5],qubits[6];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[6];
cx qubits[5],qubits[6];
t qubits[5];
tdg qubits[6];
cx qubits[2],qubits[6];
cx qubits[2],qubits[5];
t qubits[2];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[6];
h qubits[5];
cx qubits[1],qubits[5];
tdg qubits[5];
cx qubits[0],qubits[5];
t qubits[5];
cx qubits[1],qubits[5];
t qubits[1];
tdg qubits[5];
cx qubits[0],qubits[5];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[5];
h qubits[5];
cx qubits[5],qubits[6];
tdg qubits[6];
cx qubits[2],qubits[6];
t qubits[6];
cx qubits[5],qubits[6];
t qubits[5];
tdg qubits[6];
cx qubits[2],qubits[6];
cx qubits[2],qubits[5];
t qubits[2];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[6];
h qubits[6];
cx qubits[6],qubits[7];
tdg qubits[7];
cx qubits[3],qubits[7];
t qubits[7];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[3],qubits[7];
cx qubits[3],qubits[6];
t qubits[3];
tdg qubits[6];
cx qubits[3],qubits[6];
t qubits[7];
h qubits[7];
