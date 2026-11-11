OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
ry(0.2815705644039938) q[1];
rz(1.1085093551371514) q[0];
cx q[0],q[1];
