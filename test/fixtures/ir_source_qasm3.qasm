OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
gphase(pi/2);
h q[0];
t q[0];
