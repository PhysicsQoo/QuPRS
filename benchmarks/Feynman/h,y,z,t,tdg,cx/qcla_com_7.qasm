OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[24];
y qubits[0];
z qubits[0];
h qubits[2];
cx qubits[1],qubits[2];
tdg qubits[2];
cx qubits[0],qubits[2];
t qubits[2];
cx qubits[1],qubits[2];
t qubits[1];
tdg qubits[2];
cx qubits[0],qubits[2];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
t qubits[2];
h qubits[2];
y qubits[3];
z qubits[3];
h qubits[5];
cx qubits[4],qubits[5];
tdg qubits[5];
cx qubits[3],qubits[5];
t qubits[5];
cx qubits[4],qubits[5];
t qubits[4];
tdg qubits[5];
cx qubits[3],qubits[5];
cx qubits[3],qubits[4];
t qubits[3];
tdg qubits[4];
t qubits[5];
cx qubits[4],qubits[5];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[5];
cx qubits[4],qubits[5];
t qubits[4];
tdg qubits[5];
cx qubits[2],qubits[5];
cx qubits[2],qubits[4];
t qubits[2];
tdg qubits[4];
cx qubits[2],qubits[4];
t qubits[5];
h qubits[5];
y qubits[6];
z qubits[6];
h qubits[8];
h qubits[9];
cx qubits[7],qubits[9];
tdg qubits[9];
cx qubits[6],qubits[9];
t qubits[9];
cx qubits[7],qubits[9];
t qubits[7];
tdg qubits[9];
cx qubits[6],qubits[9];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
t qubits[9];
h qubits[9];
y qubits[10];
z qubits[10];
h qubits[12];
cx qubits[11],qubits[12];
tdg qubits[12];
cx qubits[10],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[10],qubits[12];
cx qubits[10],qubits[11];
t qubits[10];
tdg qubits[11];
cx qubits[11],qubits[8];
t qubits[12];
tdg qubits[8];
cx qubits[7],qubits[8];
t qubits[8];
cx qubits[11],qubits[8];
t qubits[11];
tdg qubits[8];
cx qubits[7],qubits[8];
cx qubits[7],qubits[11];
t qubits[7];
tdg qubits[11];
cx qubits[7],qubits[11];
cx qubits[11],qubits[12];
t qubits[8];
h qubits[8];
tdg qubits[12];
cx qubits[9],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[9],qubits[12];
cx qubits[9],qubits[11];
t qubits[9];
tdg qubits[11];
cx qubits[9],qubits[11];
t qubits[12];
cx qubits[8],qubits[12];
tdg qubits[12];
cx qubits[5],qubits[12];
t qubits[12];
cx qubits[8],qubits[12];
t qubits[8];
tdg qubits[12];
cx qubits[5],qubits[12];
cx qubits[5],qubits[8];
t qubits[5];
tdg qubits[8];
cx qubits[5],qubits[8];
t qubits[12];
h qubits[12];
y qubits[13];
z qubits[13];
h qubits[15];
h qubits[16];
cx qubits[14],qubits[16];
tdg qubits[16];
cx qubits[13],qubits[16];
t qubits[16];
cx qubits[14],qubits[16];
t qubits[14];
tdg qubits[16];
cx qubits[13],qubits[16];
cx qubits[13],qubits[14];
t qubits[13];
tdg qubits[14];
t qubits[16];
h qubits[16];
y qubits[17];
z qubits[17];
h qubits[20];
cx qubits[18],qubits[20];
tdg qubits[20];
cx qubits[17],qubits[20];
t qubits[20];
cx qubits[18],qubits[20];
t qubits[18];
tdg qubits[20];
cx qubits[17],qubits[20];
cx qubits[17],qubits[18];
t qubits[17];
tdg qubits[18];
cx qubits[18],qubits[15];
t qubits[20];
tdg qubits[15];
cx qubits[14],qubits[15];
t qubits[15];
cx qubits[18],qubits[15];
t qubits[18];
tdg qubits[15];
cx qubits[14],qubits[15];
cx qubits[14],qubits[18];
t qubits[14];
tdg qubits[18];
cx qubits[14],qubits[18];
cx qubits[18],qubits[20];
t qubits[15];
h qubits[15];
tdg qubits[20];
cx qubits[16],qubits[20];
t qubits[20];
cx qubits[18],qubits[20];
t qubits[18];
tdg qubits[20];
cx qubits[16],qubits[20];
cx qubits[16],qubits[18];
t qubits[16];
tdg qubits[18];
cx qubits[16],qubits[18];
t qubits[20];
h qubits[20];
y qubits[21];
z qubits[21];
h qubits[23];
cx qubits[22],qubits[23];
tdg qubits[23];
cx qubits[21],qubits[23];
t qubits[23];
cx qubits[22],qubits[23];
t qubits[22];
tdg qubits[23];
cx qubits[21],qubits[23];
cx qubits[21],qubits[22];
t qubits[21];
tdg qubits[22];
cx qubits[22],qubits[19];
t qubits[23];
tdg qubits[19];
cx qubits[15],qubits[19];
t qubits[19];
cx qubits[22],qubits[19];
t qubits[22];
tdg qubits[19];
cx qubits[15],qubits[19];
cx qubits[15],qubits[22];
t qubits[15];
tdg qubits[22];
cx qubits[15],qubits[22];
cx qubits[22],qubits[23];
t qubits[19];
h qubits[19];
tdg qubits[23];
cx qubits[20],qubits[23];
t qubits[23];
cx qubits[22],qubits[23];
t qubits[22];
tdg qubits[23];
cx qubits[20],qubits[23];
cx qubits[20],qubits[22];
t qubits[20];
tdg qubits[22];
cx qubits[20],qubits[22];
t qubits[23];
cx qubits[19],qubits[23];
tdg qubits[23];
cx qubits[12],qubits[23];
t qubits[23];
cx qubits[19],qubits[23];
t qubits[19];
tdg qubits[23];
cx qubits[12],qubits[23];
cx qubits[12],qubits[19];
t qubits[12];
tdg qubits[19];
cx qubits[12],qubits[19];
t qubits[23];
h qubits[23];
y qubits[23];
z qubits[23];
h qubits[19];
cx qubits[22],qubits[19];
tdg qubits[19];
cx qubits[15],qubits[19];
t qubits[19];
cx qubits[22],qubits[19];
t qubits[22];
tdg qubits[19];
cx qubits[15],qubits[19];
cx qubits[15],qubits[22];
t qubits[15];
tdg qubits[22];
cx qubits[15],qubits[22];
t qubits[19];
h qubits[19];
h qubits[20];
cx qubits[18],qubits[20];
tdg qubits[20];
cx qubits[16],qubits[20];
t qubits[20];
cx qubits[18],qubits[20];
t qubits[18];
tdg qubits[20];
cx qubits[16],qubits[20];
cx qubits[16],qubits[18];
t qubits[16];
tdg qubits[18];
cx qubits[16],qubits[18];
t qubits[20];
h qubits[15];
cx qubits[18],qubits[15];
tdg qubits[15];
cx qubits[14],qubits[15];
t qubits[15];
cx qubits[18],qubits[15];
t qubits[18];
tdg qubits[15];
cx qubits[14],qubits[15];
cx qubits[14],qubits[18];
t qubits[14];
tdg qubits[18];
cx qubits[14],qubits[18];
cx qubits[13],qubits[14];
cx qubits[17],qubits[18];
cx qubits[18],qubits[20];
t qubits[15];
h qubits[15];
h qubits[16];
cx qubits[14],qubits[16];
tdg qubits[16];
cx qubits[13],qubits[16];
t qubits[16];
cx qubits[14],qubits[16];
t qubits[14];
tdg qubits[16];
cx qubits[13],qubits[16];
cx qubits[13],qubits[14];
t qubits[13];
tdg qubits[14];
cx qubits[13],qubits[14];
y qubits[13];
z qubits[13];
t qubits[16];
h qubits[16];
tdg qubits[20];
cx qubits[17],qubits[20];
t qubits[20];
cx qubits[18],qubits[20];
t qubits[18];
tdg qubits[20];
cx qubits[17],qubits[20];
cx qubits[17],qubits[18];
t qubits[17];
tdg qubits[18];
cx qubits[17],qubits[18];
y qubits[17];
z qubits[17];
t qubits[20];
h qubits[20];
h qubits[12];
cx qubits[8],qubits[12];
tdg qubits[12];
cx qubits[5],qubits[12];
t qubits[12];
cx qubits[8],qubits[12];
t qubits[8];
tdg qubits[12];
cx qubits[5],qubits[12];
cx qubits[5],qubits[8];
t qubits[5];
tdg qubits[8];
cx qubits[5],qubits[8];
t qubits[12];
cx qubits[11],qubits[12];
h qubits[5];
cx qubits[4],qubits[5];
tdg qubits[5];
cx qubits[2],qubits[5];
t qubits[5];
cx qubits[4],qubits[5];
t qubits[4];
tdg qubits[5];
cx qubits[2],qubits[5];
cx qubits[2],qubits[4];
t qubits[2];
tdg qubits[4];
cx qubits[2],qubits[4];
t qubits[5];
h qubits[2];
cx qubits[1],qubits[2];
tdg qubits[2];
cx qubits[0],qubits[2];
t qubits[2];
cx qubits[1],qubits[2];
t qubits[1];
tdg qubits[2];
cx qubits[0],qubits[2];
cx qubits[0],qubits[1];
t qubits[0];
tdg qubits[1];
cx qubits[0],qubits[1];
y qubits[0];
z qubits[0];
t qubits[2];
h qubits[2];
tdg qubits[12];
cx qubits[9],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[9],qubits[12];
cx qubits[9],qubits[11];
t qubits[9];
tdg qubits[11];
cx qubits[9],qubits[11];
t qubits[12];
h qubits[8];
cx qubits[11],qubits[8];
tdg qubits[8];
cx qubits[7],qubits[8];
t qubits[8];
cx qubits[11],qubits[8];
t qubits[11];
tdg qubits[8];
cx qubits[7],qubits[8];
cx qubits[7],qubits[11];
t qubits[7];
tdg qubits[11];
cx qubits[7],qubits[11];
cx qubits[10],qubits[11];
cx qubits[11],qubits[12];
t qubits[8];
h qubits[8];
tdg qubits[12];
cx qubits[10],qubits[12];
t qubits[12];
cx qubits[11],qubits[12];
t qubits[11];
tdg qubits[12];
cx qubits[10],qubits[12];
cx qubits[10],qubits[11];
t qubits[10];
tdg qubits[11];
cx qubits[10],qubits[11];
y qubits[10];
z qubits[10];
t qubits[12];
h qubits[12];
h qubits[9];
cx qubits[21],qubits[22];
y qubits[21];
z qubits[21];
cx qubits[3],qubits[4];
cx qubits[4],qubits[5];
tdg qubits[5];
cx qubits[3],qubits[5];
t qubits[5];
cx qubits[4],qubits[5];
t qubits[4];
tdg qubits[5];
cx qubits[3],qubits[5];
cx qubits[3],qubits[4];
t qubits[3];
tdg qubits[4];
cx qubits[3],qubits[4];
y qubits[3];
z qubits[3];
t qubits[5];
h qubits[5];
cx qubits[6],qubits[7];
cx qubits[7],qubits[9];
tdg qubits[9];
cx qubits[6],qubits[9];
t qubits[9];
cx qubits[7],qubits[9];
t qubits[7];
tdg qubits[9];
cx qubits[6],qubits[9];
cx qubits[6],qubits[7];
t qubits[6];
tdg qubits[7];
cx qubits[6],qubits[7];
y qubits[6];
z qubits[6];
t qubits[9];
h qubits[9];
