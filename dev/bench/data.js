window.BENCHMARK_DATA = {
  "lastUpdate": 1767977457974,
  "repoUrl": "https://github.com/PhysicsQoo/QuPRS",
  "entries": {
    "QuPRS Benchmark History": [
      {
        "commit": {
          "author": {
            "email": "wei.jia.huang.physics@gmail.com",
            "name": "PhysicsQoo",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "wei.jia.huang.physics@gmail.com",
            "name": "PhysicsQoo",
            "username": "PhysicsQoo"
          },
          "distinct": true,
          "id": "405cf4e907076e1b184d3c7e64e1dac2dd406e09",
          "message": "delete submodules and update benchmarks.yml",
          "timestamp": "2026-01-10T00:46:32+08:00",
          "tree_id": "887bd63b5abc73f0e0c7bc097b7e15ef38c601bc",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/405cf4e907076e1b184d3c7e64e1dac2dd406e09"
        },
        "date": 1767977457618,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.3469651748072921,
            "unit": "iter/sec",
            "range": "stddev: 0.01822613642036008",
            "extra": "mean: 2.8821336336 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 1.0229303106773784,
            "unit": "iter/sec",
            "range": "stddev: 0.0033569965309475053",
            "extra": "mean: 977.5837019999983 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 1.1401113331212405,
            "unit": "iter/sec",
            "range": "stddev: 0.0025896342255813786",
            "extra": "mean: 877.1073236000007 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 1.0547963913203748,
            "unit": "iter/sec",
            "range": "stddev: 0.005795013975774082",
            "extra": "mean: 948.0502666000007 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 1.1337543653672852,
            "unit": "iter/sec",
            "range": "stddev: 0.0066187942900246205",
            "extra": "mean: 882.0252697999933 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 1.1246503586589884,
            "unit": "iter/sec",
            "range": "stddev: 0.014876829720099276",
            "extra": "mean: 889.1652346000058 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.9811482737779973,
            "unit": "iter/sec",
            "range": "stddev: 0.007509935040181521",
            "extra": "mean: 1.0192139422000026 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.9751878335177375,
            "unit": "iter/sec",
            "range": "stddev: 0.008425601311835442",
            "extra": "mean: 1.0254434742 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 0.90862381152648,
            "unit": "iter/sec",
            "range": "stddev: 0.005904865471565053",
            "extra": "mean: 1.1005654786000036 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.5277837391097718,
            "unit": "iter/sec",
            "range": "stddev: 0.00656201803509965",
            "extra": "mean: 1.8947154409999996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 0.6359658673954404,
            "unit": "iter/sec",
            "range": "stddev: 0.008269903832818979",
            "extra": "mean: 1.5724114315999997 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.4021021512195913,
            "unit": "iter/sec",
            "range": "stddev: 0.021460249064770297",
            "extra": "mean: 2.486930241400006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.3291481604923731,
            "unit": "iter/sec",
            "range": "stddev: 0.0122059173526564",
            "extra": "mean: 3.0381454920000124 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.32087508097158307,
            "unit": "iter/sec",
            "range": "stddev: 0.021310101492800215",
            "extra": "mean: 3.1164775930000017 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 0.9644416356200729,
            "unit": "iter/sec",
            "range": "stddev: 0.0031456933351297787",
            "extra": "mean: 1.0368693791999817 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 0.5557471296185944,
            "unit": "iter/sec",
            "range": "stddev: 0.00416700220957519",
            "extra": "mean: 1.7993795139999975 sec\nrounds: 5"
          }
        ]
      }
    ]
  }
}