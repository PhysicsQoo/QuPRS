# import random

# from qiskit import transpile

# from QuPRS import check_equivalence
# from QuPRS.interface.load_qiskit import build_circuit
# from QuPRS.utils.Qiskit_Circuit_Utils import pqc_generator, random_circuit


# def test_random_pqc():
#     """
#     A random test function that does nothing.
#     """
#     function_name_list = [
#         "NLocal",
#         "ExcitationPreserving",
#         "RealAmplitudes",
#         "EfficientSU2",
#         "PauliTwoDesign",
#     ]
#     for function_name in function_name_list:
#         print(f"Generated circuit for {function_name}")
#         cir1, cir2, name = pqc_generator(
#             qubit_num=3, reps=1, function_name=function_name
#         )
#         ps_cir1 = build_circuit(cir1)
#         ps_cir2 = build_circuit(cir2)

#         print(f"Generated circuit 1: {ps_cir1}")
#         print(f"Generated circuit 2: {ps_cir2}")


# def test_random_Clifford():
#     for _ in range(10):
#         print("Generating random Clifford circuit...")
#         cir = random_circuit(
#             num_qubits=random.randint(5, 10),
#             num_gates=random.randint(30, 50),
#             gates="Clifford",
#         )

#         cir2 = transpile(
#             cir,
#             basis_gates=[
#                 "x",
#                 "y",
#                 "z",
#                 "h",
#                 "s",
#                 "sdg",
#                 "sx",
#                 "sxdg",
#                 "cx",
#                 "cy",
#                 "cz",
#             ],
#             optimization_level=1,
#         )
#         print(cir == cir2)
#         result = check_equivalence(cir, cir2)
#         print(result)
#         assert (
#             result.equivalent == "equivalent" or result.equivalent == "equivalent*"
#         ), f"Expected equivalent or equivalent*, got {result.equivalent}"


# def test_random_Clifford_T():
#     for _ in range(10):
#         print("Generating random Clifford+T circuit...")
#         cir = random_circuit(
#             num_qubits=random.randint(5, 10),
#             num_gates=random.randint(30, 50),
#             gates="Clifford+T",
#         )
#         # operations_counts = cir.count_ops()
#         # gate_set = operations_counts.keys()
#         # print(f"Generated circuit with gates: {gate_set})
#         # print(f"Generated circuit with counts: {operations_counts}")

#         cir2 = transpile(
#             cir,
#             basis_gates=[
#                 "x",
#                 "y",
#                 "z",
#                 "h",
#                 "s",
#                 "sdg",
#                 "t",
#                 "tdg",
#                 "sx",
#                 "sxdg",
#                 "cx",
#                 "cy",
#                 "cz",
#                 "ch",
#             ],
#             optimization_level=1,
#         )
#         print(cir == cir2)
#         result = check_equivalence(cir, cir2)
#         print(result)
#         assert (
#             result.equivalent == "equivalent" or result.equivalent == "equivalent*"
#         ), f"Expected equivalent or equivalent*, got {result.equivalent}"


# # def test_random_Clifford_T2():
# #     for _ in range(10):
# #         from QuPRS.utils.Qiskit_Circuit_Utils import random_clifford_T_circuit
# #         cir = random_clifford_T_circuit(
# #             num_qubits=random.randint(5, 10),
# #             num_gates=random.randint(30, 50),
# #         )
# #         print("Generating random Clifford+T circuit...")
# #         operations_counts = cir.count_ops()
# #         gate_set = operations_counts.keys()
# #         print(f"Generated circuit with gates: {gate_set}")
# #         print(f" counts: {operations_counts}")

# #         cir2 = transpile(
# #             cir,
# #             basis_gates=[
# #                 "x",
# #                 "y",
# #                 "z",
# #                 "h",
# #                 "s",
# #                 "sdg",
# #                 "t",
# #                 "tdg",
# #                 "sx",
# #                 "sxdg",
# #                 "cx",
# #                 "cy",
# #                 "cz",
# #                 "ch",
# #             ],
# #             optimization_level=1,
# #         )
# #         result = check_equivalence(cir, cir2)
# #         assert (
# #             result.equivalent == "equivalent" or result.equivalent == "equivalent*"
# #         ), f"Expected equivalent or equivalent*, got {result.equivalent}"


# if __name__ == "__main__":
#     test_random_pqc()
#     test_random_Clifford()
#     test_random_Clifford_T()

#     # test_random_Clifford_T2()
