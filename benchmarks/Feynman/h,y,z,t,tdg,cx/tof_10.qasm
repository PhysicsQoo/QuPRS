OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[19];
h qubits[10];
cx qubits[1],qubits[10];
tdg qubits[10];
cx qubits[0],qubits[10];
t qubits[10];
cx qubits[1],qubits[10];
t qubits[1];
tdg qubits[10];
cx qubits[0],qubits[10];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[10];
h qubits[10];
h qubits[11];
cx qubits[10],qubits[11];
tdg qubits[11];
cx qubits[2],qubits[11];
t qubits[11];
cx qubits[10],qubits[11];
t qubits[10];
tdg qubits[11];
cx qubits[2],qubits[11];
cx qubits[2],qubits[10];
t qubits[2];
tdg qubits[10];
cx qubits[2],qubits[10];
t qubits[11];
h qubits[11];
h qubits[12];
cx qubits[11],qubits[12];
tdg qubits[12];
cx qubits[3],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[3],qubits[12];
cx qubits[3],qubits[11];
t qubits[3];
tdg qubits[11];
cx qubits[3],qubits[11];
t qubits[12];
h qubits[12];
h qubits[13];
cx qubits[12],qubits[13];
tdg qubits[13];
cx qubits[4],qubits[13];
t qubits[13];
cx qubits[12],qubits[13];
t qubits[12];
tdg qubits[13];
cx qubits[4],qubits[13];
cx qubits[4],qubits[12];
t qubits[4];
tdg qubits[12];
cx qubits[4],qubits[12];
t qubits[13];
h qubits[13];
h qubits[14];
cx qubits[13],qubits[14];
tdg qubits[14];
cx qubits[5],qubits[14];
t qubits[14];
cx qubits[13],qubits[14];
t qubits[13];
tdg qubits[14];
cx qubits[5],qubits[14];
cx qubits[5],qubits[13];
t qubits[5];
tdg qubits[13];
cx qubits[5],qubits[13];
t qubits[14];
h qubits[14];
h qubits[15];
cx qubits[14],qubits[15];
tdg qubits[15];
cx qubits[6],qubits[15];
t qubits[15];
cx qubits[14],qubits[15];
t qubits[14];
tdg qubits[15];
cx qubits[6],qubits[15];
cx qubits[6],qubits[14];
t qubits[6];
tdg qubits[14];
cx qubits[6],qubits[14];
t qubits[15];
h qubits[15];
h qubits[16];
cx qubits[15],qubits[16];
tdg qubits[16];
cx qubits[7],qubits[16];
t qubits[16];
cx qubits[15],qubits[16];
t qubits[15];
tdg qubits[16];
cx qubits[7],qubits[16];
cx qubits[7],qubits[15];
t qubits[7];
tdg qubits[15];
cx qubits[7],qubits[15];
t qubits[16];
h qubits[16];
h qubits[17];
cx qubits[16],qubits[17];
tdg qubits[17];
cx qubits[8],qubits[17];
t qubits[17];
cx qubits[16],qubits[17];
t qubits[16];
tdg qubits[17];
cx qubits[8],qubits[17];
cx qubits[8],qubits[16];
t qubits[8];
tdg qubits[16];
cx qubits[8],qubits[16];
t qubits[17];
h qubits[17];
h qubits[18];
cx qubits[17],qubits[18];
tdg qubits[18];
cx qubits[9],qubits[18];
t qubits[18];
cx qubits[17],qubits[18];
t qubits[17];
tdg qubits[18];
cx qubits[9],qubits[18];
cx qubits[9],qubits[17];
t qubits[9];
tdg qubits[17];
cx qubits[9],qubits[17];
t qubits[18];
h qubits[18];
h qubits[17];
cx qubits[16],qubits[17];
tdg qubits[17];
cx qubits[8],qubits[17];
t qubits[17];
cx qubits[16],qubits[17];
t qubits[16];
tdg qubits[17];
cx qubits[8],qubits[17];
cx qubits[8],qubits[16];
t qubits[8];
tdg qubits[16];
cx qubits[8],qubits[16];
t qubits[17];
h qubits[17];
h qubits[16];
cx qubits[15],qubits[16];
tdg qubits[16];
cx qubits[7],qubits[16];
t qubits[16];
cx qubits[15],qubits[16];
t qubits[15];
tdg qubits[16];
cx qubits[7],qubits[16];
cx qubits[7],qubits[15];
t qubits[7];
tdg qubits[15];
cx qubits[7],qubits[15];
t qubits[16];
h qubits[16];
h qubits[15];
cx qubits[14],qubits[15];
tdg qubits[15];
cx qubits[6],qubits[15];
t qubits[15];
cx qubits[14],qubits[15];
t qubits[14];
tdg qubits[15];
cx qubits[6],qubits[15];
cx qubits[6],qubits[14];
t qubits[6];
tdg qubits[14];
cx qubits[6],qubits[14];
t qubits[15];
h qubits[15];
h qubits[14];
cx qubits[13],qubits[14];
tdg qubits[14];
cx qubits[5],qubits[14];
t qubits[14];
cx qubits[13],qubits[14];
t qubits[13];
tdg qubits[14];
cx qubits[5],qubits[14];
cx qubits[5],qubits[13];
t qubits[5];
tdg qubits[13];
cx qubits[5],qubits[13];
t qubits[14];
h qubits[14];
h qubits[13];
cx qubits[12],qubits[13];
tdg qubits[13];
cx qubits[4],qubits[13];
t qubits[13];
cx qubits[12],qubits[13];
t qubits[12];
tdg qubits[13];
cx qubits[4],qubits[13];
cx qubits[4],qubits[12];
t qubits[4];
tdg qubits[12];
cx qubits[4],qubits[12];
t qubits[13];
h qubits[13];
h qubits[12];
cx qubits[11],qubits[12];
tdg qubits[12];
cx qubits[3],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[3],qubits[12];
cx qubits[3],qubits[11];
t qubits[3];
tdg qubits[11];
cx qubits[3],qubits[11];
t qubits[12];
h qubits[12];
h qubits[11];
cx qubits[10],qubits[11];
tdg qubits[11];
cx qubits[2],qubits[11];
t qubits[11];
cx qubits[10],qubits[11];
t qubits[10];
tdg qubits[11];
cx qubits[2],qubits[11];
cx qubits[2],qubits[10];
t qubits[2];
tdg qubits[10];
cx qubits[2],qubits[10];
t qubits[11];
h qubits[11];
h qubits[10];
cx qubits[1],qubits[10];
tdg qubits[10];
cx qubits[0],qubits[10];
t qubits[10];
cx qubits[1],qubits[10];
t qubits[1];
tdg qubits[10];
cx qubits[0],qubits[10];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[10];
h qubits[10];
