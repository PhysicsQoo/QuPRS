OPENQASM 2.0;
include "qelib1.inc";
qreg node[3];
qreg coin[1];
ry(-pi/2) node[0];
rz(-7*pi/8) node[0];
rz(pi/8) node[1];
rz(pi/8) node[2];
ry(-pi/2) coin[0];
rz(-4.543701221170002) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
ry(pi/2) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
ry(-pi/2) coin[0];
cx node[0],coin[0];
ry(pi/2) node[0];
rz(-7*pi/8) node[0];
ry(pi/2) coin[0];
rz(1.402108567580207) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
rz(3.686161821799056) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
rz(pi/8) node[1];
cx coin[0],node[2];
rz(5*pi/8) node[2];
ry(pi) node[2];
ry(pi) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
ry(pi/2) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(-2.5802058126763807) coin[0];
ry(-pi/2) coin[0];
cx node[0],coin[0];
ry(pi/2) node[0];
rz(-7*pi/8) node[0];
ry(pi/2) coin[0];
rz(-0.5613868409134142) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
rz(pi/8) node[1];
cx coin[0],node[2];
rz(5*pi/8) node[2];
ry(pi) node[2];
ry(-pi/2) coin[0];
rz(-1.4021085675802087) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
ry(pi/2) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
ry(-pi/2) coin[0];
cx node[0],coin[0];
ry(pi/2) node[0];
rz(-7*pi/8) node[0];
ry(pi/2) coin[0];
rz(1.402108567580207) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
rx(2.567800546811197) node[0];
rz(pi/8) node[1];
cx coin[0],node[2];
rz(5*pi/8) node[2];
ry(pi) node[2];
ry(pi) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
ry(pi/2) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(-2.5802058126763807) coin[0];
ry(-pi/2) coin[0];
cx node[0],coin[0];
ry(pi/2) node[0];
rz(-7*pi/8) node[0];
ry(pi/2) coin[0];
rz(-0.5613868409134142) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
rz(pi/8) node[1];
cx coin[0],node[2];
rz(5*pi/8) node[2];
ry(pi) node[2];
ry(-pi/2) coin[0];
rz(-1.4021085675802087) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
rz(2.0970319457684212) node[0];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
ry(pi/2) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
ry(-pi/2) coin[0];
cx node[0],coin[0];
ry(pi/2) node[0];
rz(-7*pi/8) node[0];
ry(pi/2) coin[0];
rz(1.402108567580207) coin[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
rz(pi/8) node[1];
cx coin[0],node[2];
rz(5*pi/8) node[2];
ry(pi) node[2];
ry(pi) coin[0];
cx coin[0],node[1];
rz(-pi/8) node[1];
cx coin[0],node[1];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
rz(pi/8) node[2];
cx node[1],node[2];
rz(-pi/8) node[2];
cx coin[0],node[2];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx coin[0],node[0];
rz(pi/8) node[0];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[1],node[0];
rz(pi/8) node[0];
ry(-pi/2) node[1];
rz(-pi) node[1];
cx node[2],node[0];
rz(-pi/8) node[0];
cx node[2],node[1];
rz(-pi/4) node[1];
cx coin[0],node[0];
ry(-pi/2) node[0];
rz(-pi) node[0];
cx coin[0],node[1];
rz(pi/4) node[1];
cx node[2],node[1];
rz(-pi/4) node[1];
rz(pi/4) node[2];
cx coin[0],node[1];
rz(pi/4) node[1];
ry(pi/2) node[1];
cx coin[0],node[2];
rz(3*pi/4) node[2];
ry(pi) node[2];
ry(pi) coin[0];
rz(pi) coin[0];
