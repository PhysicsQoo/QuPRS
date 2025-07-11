OPENQASM 2.0;
include "qelib1.inc";
qreg q[7];
qreg psi[1];
rz(pi/2) q[0];
rx(pi/2) q[0];
rz(pi/2) q[0];
rz(pi/2) q[1];
rx(pi/2) q[1];
rz(pi/2) q[1];
rz(pi/2) q[2];
rx(pi/2) q[2];
rz(pi/2) q[2];
rz(pi/2) q[3];
rx(pi/2) q[3];
rz(pi/2) q[3];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
rz(pi/2) q[5];
rx(pi/2) q[5];
rz(pi/2) q[5];
rz(pi/2) q[6];
rx(pi/2) q[6];
rz(pi/2) q[6];
x psi[0];
rz(-1.3499030933393643) psi[0];
z psi[0];
cx psi[0],q[0];
rz(1.3499030933393643) q[0];
cx psi[0],q[0];
rz(-1.3499030933393643) q[0];
rz(0.44178646691106466) psi[0];
cx psi[0],q[1];
rz(-0.44178646691106466) q[1];
cx psi[0],q[1];
rz(0.44178646691106466) q[1];
rz(0.8835729338221293) psi[0];
cx psi[0],q[2];
rz(-0.8835729338221293) q[2];
cx psi[0],q[2];
rz(0.8835729338221293) q[2];
rz(-7*pi/16) psi[0];
cx psi[0],q[3];
rz(7*pi/16) q[3];
cx psi[0],q[3];
rz(-7*pi/16) q[3];
rz(-pi/16) q[3];
rz(pi/8) psi[0];
cx psi[0],q[4];
rz(-pi/8) q[4];
cx psi[0],q[4];
rz(pi/8) q[4];
cx q[2],q[4];
cx q[4],q[2];
cx q[2],q[4];
rz(-pi/8) q[2];
rz(-pi/32) q[4];
rz(pi/4) psi[0];
cx psi[0],q[5];
rz(-pi/4) q[5];
cx psi[0],q[5];
rz(pi/4) q[5];
cx q[1],q[5];
cx q[5],q[1];
cx q[1],q[5];
rz(-pi/4) q[1];
rz(-pi/64) q[5];
rz(pi/2) psi[0];
cx psi[0],q[6];
rz(-pi/2) q[6];
cx psi[0],q[6];
rz(pi/2) q[6];
cx q[0],q[6];
cx q[6],q[0];
cx q[0],q[6];
rz(pi/2) q[0];
rx(pi/2) q[0];
rz(pi/2) q[0];
cx q[1],q[0];
rz(pi/4) q[0];
cx q[1],q[0];
rz(-pi/4) q[0];
rz(pi/2) q[1];
rx(pi/2) q[1];
rz(pi/2) q[1];
cx q[2],q[0];
rz(pi/8) q[0];
cx q[2],q[0];
rz(-pi/8) q[0];
rz(-pi/4) q[2];
cx q[2],q[1];
rz(pi/4) q[1];
cx q[2],q[1];
rz(-pi/4) q[1];
rz(pi/2) q[2];
rx(pi/2) q[2];
rz(pi/2) q[2];
cx q[3],q[0];
rz(pi/16) q[0];
cx q[3],q[0];
rz(-pi/16) q[0];
rz(-pi/8) q[3];
cx q[3],q[1];
rz(pi/8) q[1];
cx q[3],q[1];
rz(-pi/8) q[1];
rz(-pi/4) q[3];
cx q[3],q[2];
rz(pi/4) q[2];
cx q[3],q[2];
rz(-pi/4) q[2];
rz(pi/2) q[3];
rx(pi/2) q[3];
rz(pi/2) q[3];
cx q[4],q[0];
rz(pi/32) q[0];
cx q[4],q[0];
rz(-pi/32) q[0];
rz(-pi/16) q[4];
cx q[4],q[1];
rz(pi/16) q[1];
cx q[4],q[1];
rz(-pi/16) q[1];
rz(-pi/8) q[4];
cx q[4],q[2];
rz(pi/8) q[2];
cx q[4],q[2];
rz(-pi/8) q[2];
rz(-pi/4) q[4];
cx q[4],q[3];
rz(pi/4) q[3];
cx q[4],q[3];
rz(-pi/4) q[3];
rz(pi/2) q[4];
rx(pi/2) q[4];
rz(pi/2) q[4];
cx q[5],q[0];
rz(pi/64) q[0];
cx q[5],q[0];
rz(-pi/64) q[0];
rz(-pi/32) q[5];
cx q[5],q[1];
rz(pi/32) q[1];
cx q[5],q[1];
rz(-pi/32) q[1];
rz(-pi/16) q[5];
cx q[5],q[2];
rz(pi/16) q[2];
cx q[5],q[2];
rz(-pi/16) q[2];
rz(-pi/8) q[5];
cx q[5],q[3];
rz(pi/8) q[3];
cx q[5],q[3];
rz(-pi/8) q[3];
rz(-pi/4) q[5];
cx q[5],q[4];
rz(pi/4) q[4];
cx q[5],q[4];
rz(-pi/4) q[4];
rz(pi/2) q[5];
rx(pi/2) q[5];
rz(pi/2) q[5];
rz(-pi/128) q[6];
cx q[6],q[0];
rz(pi/128) q[0];
cx q[6],q[0];
rz(-pi/128) q[0];
rz(-pi/64) q[6];
cx q[6],q[1];
rz(pi/64) q[1];
cx q[6],q[1];
rz(-pi/64) q[1];
rz(-pi/32) q[6];
cx q[6],q[2];
rz(pi/32) q[2];
cx q[6],q[2];
rz(-pi/32) q[2];
rz(-pi/16) q[6];
cx q[6],q[3];
rz(pi/16) q[3];
cx q[6],q[3];
rz(-pi/16) q[3];
rz(-pi/8) q[6];
cx q[6],q[4];
rz(pi/8) q[4];
cx q[6],q[4];
rz(-pi/8) q[4];
rz(-pi/4) q[6];
cx q[6],q[5];
rz(pi/4) q[5];
cx q[6],q[5];
rz(-pi/4) q[5];
rz(pi/2) q[6];
rx(pi/2) q[6];
rz(pi/2) q[6];
