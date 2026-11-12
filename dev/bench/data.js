window.BENCHMARK_DATA = {
  "lastUpdate": 1794461371966,
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
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "1fdec16f6440d369b202c209173c60312513840c",
          "message": "Fix Ganak/GPMC Build Issues, Enable Cross-Platform CI (#16)\n\n* build: modernize build system with cross-platform support and caching\n- Integrate `cibuildwheel` for multi-arch (x86/ARM) and macOS wheels.\n- Enable CI caching for compiled binaries to speed up tests/benchmarks.\n- Replace tracked binaries with git submodules (GPMC/Ganak) and recursive checkout.\n- Standardize installed binary names (strip extensions) to simplify runtime lookup.\n- Update [pyproject.toml] to include compiled artifacts in wheels.\n\n* add \"-DCMAKE_POLICY_VERSION_MINIMUM=3.5\"\n\n* add run workflows on scripts/hatch_build.py change\n\n* Change ganak from build to download\n\n* Fix Ganak download link and parse code.\n\n* Update python-publish.yml to change build(ci): configure cibuildwheel for cross-platform builds\n\n* ci: enable multi-arch docker build and fix benchmark dependencies\n\n* change cache key\n\n* ci: harden build system and force cache refresh\n\n* Fixed Binary Location\n\n* update dependency\n\n* update dependency\n\n* update report logic\n\n* ci: optimize benchmark workflow\n- Consolidate \"Run\" and \"Compare\" steps to avoid double execution.\n- Ensure benchmark reports are generated even on regression failures.",
          "timestamp": "2026-01-11T22:06:36+08:00",
          "tree_id": "62fb73c765ad0a8413ef49abcbb93c4383ece4d1",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/1fdec16f6440d369b202c209173c60312513840c"
        },
        "date": 1768140776621,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.3354711739335477,
            "unit": "iter/sec",
            "range": "stddev: 0.04928760824084533",
            "extra": "mean: 2.9808820480000064 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 0.9144470840349698,
            "unit": "iter/sec",
            "range": "stddev: 0.04212188297520454",
            "extra": "mean: 1.093556989199999 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 1.0711891256923098,
            "unit": "iter/sec",
            "range": "stddev: 0.021619674274664047",
            "extra": "mean: 933.5419637999962 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 0.9412391162746653,
            "unit": "iter/sec",
            "range": "stddev: 0.032411324602474124",
            "extra": "mean: 1.0624292836000109 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 1.050301823102802,
            "unit": "iter/sec",
            "range": "stddev: 0.02600736713081963",
            "extra": "mean: 952.1072685999911 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 0.9973244873714933,
            "unit": "iter/sec",
            "range": "stddev: 0.04677266344107526",
            "extra": "mean: 1.0026826902000152 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.8672991550524629,
            "unit": "iter/sec",
            "range": "stddev: 0.03731271457344708",
            "extra": "mean: 1.1530046975999995 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.8729412866953454,
            "unit": "iter/sec",
            "range": "stddev: 0.03440756292136992",
            "extra": "mean: 1.1455524159999981 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 0.8369642003725717,
            "unit": "iter/sec",
            "range": "stddev: 0.03850406649827765",
            "extra": "mean: 1.1947942332000026 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.5111400971822245,
            "unit": "iter/sec",
            "range": "stddev: 0.08337920087208495",
            "extra": "mean: 1.956410787400023 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 0.5933019821324859,
            "unit": "iter/sec",
            "range": "stddev: 0.016913468443418657",
            "extra": "mean: 1.685482317800006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.3459510540475281,
            "unit": "iter/sec",
            "range": "stddev: 0.10450384294258372",
            "extra": "mean: 2.8905823187999773 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.3106773865102717,
            "unit": "iter/sec",
            "range": "stddev: 0.09658216495287815",
            "extra": "mean: 3.2187730534000023 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.3110775623444556,
            "unit": "iter/sec",
            "range": "stddev: 0.03109269464576456",
            "extra": "mean: 3.214632365199975 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 0.8878622528977294,
            "unit": "iter/sec",
            "range": "stddev: 0.0257431543482727",
            "extra": "mean: 1.1263008386000024 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 0.5468436387394738,
            "unit": "iter/sec",
            "range": "stddev: 0.005469276238202523",
            "extra": "mean: 1.828676296399999 sec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "e78ef850fac89383dda2647d6d69b6c694e5d60c",
          "message": "ci: harden build pipeline with multi-arch and publish verification (#17)\n\n* Only commit main_baseline.json not all files\n\n* ci(docker): add arm64 build check and fix cross-compilation\n\n- Patch `GPMC/core/Main.cc` in `hatch_build.py` to fix ARM64 compilation.\n- Add `check-arm64-build` job to PR workflow to verify cross-compilation.\n- Fix `docker-build.yml` to ensure robust multi-arch support.\n\n* ci: harden build pipeline with multi-arch support and verification",
          "timestamp": "2026-01-11T23:07:16+08:00",
          "tree_id": "a1aba29d2fa9e27b5ffc118b354db562da8d9cb5",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/e78ef850fac89383dda2647d6d69b6c694e5d60c"
        },
        "date": 1768144277655,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.39044032017290037,
            "unit": "iter/sec",
            "range": "stddev: 0.004317659809766244",
            "extra": "mean: 2.5612108901999817 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 1.1193944714948936,
            "unit": "iter/sec",
            "range": "stddev: 0.0062846014949820665",
            "extra": "mean: 893.3401276000154 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 1.2557671110855206,
            "unit": "iter/sec",
            "range": "stddev: 0.005171235412316165",
            "extra": "mean: 796.3259996000147 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 1.1435367861068049,
            "unit": "iter/sec",
            "range": "stddev: 0.005902792862920012",
            "extra": "mean: 874.4799573999899 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 1.218858870713983,
            "unit": "iter/sec",
            "range": "stddev: 0.007588630731084379",
            "extra": "mean: 820.4395308000016 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 1.2198978122587996,
            "unit": "iter/sec",
            "range": "stddev: 0.013344551831701225",
            "extra": "mean: 819.7407930000054 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 1.0438942602483043,
            "unit": "iter/sec",
            "range": "stddev: 0.00876054648212563",
            "extra": "mean: 957.9514306000078 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 1.0625977207766322,
            "unit": "iter/sec",
            "range": "stddev: 0.009444850038306795",
            "extra": "mean: 941.0899162000078 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 0.9857004632902087,
            "unit": "iter/sec",
            "range": "stddev: 0.0033739548686928513",
            "extra": "mean: 1.0145069797999895 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.5338199477111846,
            "unit": "iter/sec",
            "range": "stddev: 0.0063256522886073925",
            "extra": "mean: 1.8732908058000022 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 0.6796855962133991,
            "unit": "iter/sec",
            "range": "stddev: 0.007353305172674811",
            "extra": "mean: 1.4712684887999785 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.35794431245793557,
            "unit": "iter/sec",
            "range": "stddev: 0.020382965002819133",
            "extra": "mean: 2.7937306592000026 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.34315881883391874,
            "unit": "iter/sec",
            "range": "stddev: 0.012180586163910906",
            "extra": "mean: 2.914102582000021 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.32655297738648276,
            "unit": "iter/sec",
            "range": "stddev: 0.012149060903784885",
            "extra": "mean: 3.0622902538000063 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 1.0426999745211478,
            "unit": "iter/sec",
            "range": "stddev: 0.0052710744877287555",
            "extra": "mean: 959.048647200018 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 0.5636633236879783,
            "unit": "iter/sec",
            "range": "stddev: 0.002115232206962843",
            "extra": "mean: 1.7741086886000061 sec\nrounds: 5"
          }
        ]
      },
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
          "id": "dd1ea5918121c85989c8bc605a6324a323976507",
          "message": "add github-token in benchmarks.yml",
          "timestamp": "2026-01-11T23:47:30+08:00",
          "tree_id": "742aa1c5c77dbceec69a5b622bc306d4fbb2c498",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/dd1ea5918121c85989c8bc605a6324a323976507"
        },
        "date": 1768146725259,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.34729392351272825,
            "unit": "iter/sec",
            "range": "stddev: 0.02173376030591995",
            "extra": "mean: 2.879405403600015 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 1.0340985727437324,
            "unit": "iter/sec",
            "range": "stddev: 0.019746693778204837",
            "extra": "mean: 967.0258003999948 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 1.1464937749896085,
            "unit": "iter/sec",
            "range": "stddev: 0.0039933582795986374",
            "extra": "mean: 872.2245351999959 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 1.0289370578154104,
            "unit": "iter/sec",
            "range": "stddev: 0.03632415671454906",
            "extra": "mean: 971.8767463999711 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 1.1212330793620104,
            "unit": "iter/sec",
            "range": "stddev: 0.012157200238333072",
            "extra": "mean: 891.8752205999908 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 1.1265520054104305,
            "unit": "iter/sec",
            "range": "stddev: 0.005257370823154096",
            "extra": "mean: 887.6643024000259 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.9950715410117194,
            "unit": "iter/sec",
            "range": "stddev: 0.0037544049992437076",
            "extra": "mean: 1.0049528690000216 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.9796373549246353,
            "unit": "iter/sec",
            "range": "stddev: 0.012034103209062041",
            "extra": "mean: 1.0207859009999993 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 0.8952931719482607,
            "unit": "iter/sec",
            "range": "stddev: 0.00680881201309245",
            "extra": "mean: 1.1169525595999859 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.5329034268092374,
            "unit": "iter/sec",
            "range": "stddev: 0.004832081241780393",
            "extra": "mean: 1.8765126093999924 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 0.6253973980666804,
            "unit": "iter/sec",
            "range": "stddev: 0.056888205112520795",
            "extra": "mean: 1.5989833073999762 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.3601893681743124,
            "unit": "iter/sec",
            "range": "stddev: 0.02844921990897612",
            "extra": "mean: 2.7763173717999736 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.328382908662897,
            "unit": "iter/sec",
            "range": "stddev: 0.013638252107032667",
            "extra": "mean: 3.0452254779999977 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.3232989286741169,
            "unit": "iter/sec",
            "range": "stddev: 0.015294730027734618",
            "extra": "mean: 3.093112631400004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 0.9576417307798517,
            "unit": "iter/sec",
            "range": "stddev: 0.014173689276008476",
            "extra": "mean: 1.044231853999986 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 0.552620065643473,
            "unit": "iter/sec",
            "range": "stddev: 0.03382326849256811",
            "extra": "mean: 1.8095615091999888 sec\nrounds: 5"
          }
        ]
      },
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
          "id": "c228a2e2ed6c9ad9107224b8f1da6bcaecf03b2d",
          "message": "chore: fix ci and build scripts",
          "timestamp": "2026-01-12T01:31:18+08:00",
          "tree_id": "8102049f1e1b78062943eba2865b6c3559ed0517",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/c228a2e2ed6c9ad9107224b8f1da6bcaecf03b2d"
        },
        "date": 1768152973862,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.3339930778089641,
            "unit": "iter/sec",
            "range": "stddev: 0.018982251298318167",
            "extra": "mean: 2.994074028600005 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 0.9233487774127251,
            "unit": "iter/sec",
            "range": "stddev: 0.02049370776974191",
            "extra": "mean: 1.0830143759999942 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 1.0233912614910092,
            "unit": "iter/sec",
            "range": "stddev: 0.02014304612467452",
            "extra": "mean: 977.1433836000028 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 0.941984856369979,
            "unit": "iter/sec",
            "range": "stddev: 0.021038445216189836",
            "extra": "mean: 1.0615881914000056 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 1.0392577304689647,
            "unit": "iter/sec",
            "range": "stddev: 0.016112460390866758",
            "extra": "mean: 962.2252215999879 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 1.0351216918396189,
            "unit": "iter/sec",
            "range": "stddev: 0.016116368671648874",
            "extra": "mean: 966.0699876000081 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.8953606498980957,
            "unit": "iter/sec",
            "range": "stddev: 0.01743638672940548",
            "extra": "mean: 1.1168683815999885 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.9019697078643636,
            "unit": "iter/sec",
            "range": "stddev: 0.021318553645329072",
            "extra": "mean: 1.1086846834000084 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 0.8297976413716458,
            "unit": "iter/sec",
            "range": "stddev: 0.0304259330257191",
            "extra": "mean: 1.205113090399982 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.5000223167960326,
            "unit": "iter/sec",
            "range": "stddev: 0.017695399313566774",
            "extra": "mean: 1.9999107368000069 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 0.5770164346535213,
            "unit": "iter/sec",
            "range": "stddev: 0.028079779359234433",
            "extra": "mean: 1.7330528906000153 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.34318154642711335,
            "unit": "iter/sec",
            "range": "stddev: 0.02072005077549535",
            "extra": "mean: 2.9139095922000138 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.3049431983515058,
            "unit": "iter/sec",
            "range": "stddev: 0.027707319640607273",
            "extra": "mean: 3.279299244599997 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.30394173282822423,
            "unit": "iter/sec",
            "range": "stddev: 0.032912014671775076",
            "extra": "mean: 3.2901042930000015 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 0.8845267352979632,
            "unit": "iter/sec",
            "range": "stddev: 0.01252376990424952",
            "extra": "mean: 1.1305480773999874 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 0.525027471372032,
            "unit": "iter/sec",
            "range": "stddev: 0.03012811799498936",
            "extra": "mean: 1.904662240599987 sec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "d62d3eb24fe126753d3d5a7d53d28a0f9cf2065d",
          "message": "Enhance Multi-Platform CI/CD, macOS Build Reliability, and Tool Stability (#19)\n\n* feat: 🚀 Update CI/CD workflows to support multi-platform test, builds and pushes.\n- Updated Readme.md and pyproject.toml\n\n* Fix(ci): Update caching keys for benchmarks and pytest workflows to support multi-platform builds.\n\n* Fix(ci) : Fix pytest.yml Install system dependencies step and benchmarks.yml typo\n\n* fix: 🐛 Remove Python 3.14 from supported versions and add zlib to macOS dependencies\n\n* fix: 🐛 Update macOS compiler paths to include zlib in environment variables\n\n* fix: 🐛 Update macOS environment variables for CFLAGS and LDFLAGS in CI workflows\n\n* fix: 🐛 Update caching keys for wmc_tools in CI workflows to v0\n\n* fix: 🐛 Add DYLD_LIBRARY_PATH to macOS environment variables in CI workflows\n\n* fix: 🐛 add ulimit setting to solve pytest limit\n\n* Fix: 🐛 Added ulimit setting to display the state before and after the limit change.\n\n* fix: 🐛 Handle ganak runtime crashes in benchmark tests (Skip if ganak have bug)\n\n* fix: 🐛 Update workflow paths from 'tests/**' to 'test/**'\n\n* fix: 🐛 Handle unexpected errors in Ganak tool during benchmark tests\n\n* refactor: ✨ Improve code readability and maintainability across multiple files\n\n- Cleaned up imports and removed unused ones in load_qiskit.py and ps2wmc.py.\n- Enhanced formatting and consistency in generate_benchmark_report.py and hatch_build.py.\n- Refactored strategy.py to remove old code and improve structure.\n- Added safe mode option in check_equivalence function for better memory management.\n- Updated comments and documentation for clarity in various modules.\n\n* fix: 🐛 Refactor match_Elim function and improve Ganak error messages in tests\n\n* fix: 🐛 Improve error handling for Ganak tool in benchmark tests\n\n* test: 🧪 Enhance test parameterization and add pytest-codspeed dependency",
          "timestamp": "2026-01-14T15:00:07+08:00",
          "tree_id": "294e8a3293e12ed9f0907fe06778edab94137e64",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/d62d3eb24fe126753d3d5a7d53d28a0f9cf2065d"
        },
        "date": 1768374826939,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.545443460456686,
            "unit": "iter/sec",
            "range": "stddev: 0.02776790284726884",
            "extra": "mean: 1.8333705919999943 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 11.040902588133259,
            "unit": "iter/sec",
            "range": "stddev: 0.014672018232363963",
            "extra": "mean: 90.57230530000311 msec\nrounds: 10"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-False]",
            "value": 89.73536619957343,
            "unit": "iter/sec",
            "range": "stddev: 0.00017201056267223346",
            "extra": "mean: 11.143878298506944 msec\nrounds: 67"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-False]",
            "value": 19.97232254182906,
            "unit": "iter/sec",
            "range": "stddev: 0.0003402615534006134",
            "extra": "mean: 50.06928953333537 msec\nrounds: 15"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-True]",
            "value": 28.997447968971525,
            "unit": "iter/sec",
            "range": "stddev: 0.0003819259024535746",
            "extra": "mean: 34.48579340740749 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 28.931068142697395,
            "unit": "iter/sec",
            "range": "stddev: 0.000676410578327122",
            "extra": "mean: 34.56491806896573 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-True]",
            "value": 29.152929648302425,
            "unit": "iter/sec",
            "range": "stddev: 0.00038733527556879157",
            "extra": "mean: 34.30186990000266 msec\nrounds: 30"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 29.001531138736237,
            "unit": "iter/sec",
            "range": "stddev: 0.0004414611437725176",
            "extra": "mean: 34.48093810000046 msec\nrounds: 30"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-True]",
            "value": 27.640969849683852,
            "unit": "iter/sec",
            "range": "stddev: 0.00044614229451054514",
            "extra": "mean: 36.1781806296293 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 30.942250034324754,
            "unit": "iter/sec",
            "range": "stddev: 0.00037061555072562805",
            "extra": "mean: 32.318270290320946 msec\nrounds: 31"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-True]",
            "value": 27.658720376885235,
            "unit": "iter/sec",
            "range": "stddev: 0.0004043496012899527",
            "extra": "mean: 36.15496257143239 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 30.7617048885516,
            "unit": "iter/sec",
            "range": "stddev: 0.0006276909506674875",
            "extra": "mean: 32.507951156249604 msec\nrounds: 32"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-True]",
            "value": 26.198643078334612,
            "unit": "iter/sec",
            "range": "stddev: 0.01018182323649412",
            "extra": "mean: 38.16991578571357 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 30.887714139888995,
            "unit": "iter/sec",
            "range": "stddev: 0.0003122608581551387",
            "extra": "mean: 32.37533199999998 msec\nrounds: 32"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-True]",
            "value": 27.57517087848291,
            "unit": "iter/sec",
            "range": "stddev: 0.00042275470198846054",
            "extra": "mean: 36.264507821429554 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 31.149849664074505,
            "unit": "iter/sec",
            "range": "stddev: 0.000319238240995884",
            "extra": "mean: 32.10288366666861 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 22.206662003429322,
            "unit": "iter/sec",
            "range": "stddev: 0.0004285863020640919",
            "extra": "mean: 45.0315315217376 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 22.186486352189693,
            "unit": "iter/sec",
            "range": "stddev: 0.0003246424182091177",
            "extra": "mean: 45.07248169565638 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 22.167757455748724,
            "unit": "iter/sec",
            "range": "stddev: 0.00038089209310744534",
            "extra": "mean: 45.110562130436506 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 22.225360013580435,
            "unit": "iter/sec",
            "range": "stddev: 0.00031553430786917695",
            "extra": "mean: 44.993646869565524 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 7.743312849373432,
            "unit": "iter/sec",
            "range": "stddev: 0.0006352442690712432",
            "extra": "mean: 129.1436907500021 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 7.25134525921333,
            "unit": "iter/sec",
            "range": "stddev: 0.0007891629950407242",
            "extra": "mean: 137.9054457142875 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 7.638375881772823,
            "unit": "iter/sec",
            "range": "stddev: 0.002085300916197205",
            "extra": "mean: 130.91788300000573 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 7.177018784656189,
            "unit": "iter/sec",
            "range": "stddev: 0.0024492391751183723",
            "extra": "mean: 139.33361887499984 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 7.848083667791951,
            "unit": "iter/sec",
            "range": "stddev: 0.019859737488151022",
            "extra": "mean: 127.41964055555854 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 8.071017675486083,
            "unit": "iter/sec",
            "range": "stddev: 0.000771358202821324",
            "extra": "mean: 123.9001127500039 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 8.089190573992953,
            "unit": "iter/sec",
            "range": "stddev: 0.005915304462388231",
            "extra": "mean: 123.62176300000114 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 8.127934589936867,
            "unit": "iter/sec",
            "range": "stddev: 0.0007670474007634663",
            "extra": "mean: 123.03248616666924 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 8.230527897481121,
            "unit": "iter/sec",
            "range": "stddev: 0.0005541934326309866",
            "extra": "mean: 121.49888955555828 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 8.037827121869075,
            "unit": "iter/sec",
            "range": "stddev: 0.0006134319779541321",
            "extra": "mean: 124.411732777784 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 8.298682285342691,
            "unit": "iter/sec",
            "range": "stddev: 0.0004852364992245811",
            "extra": "mean: 120.50105855555178 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 8.096582127442199,
            "unit": "iter/sec",
            "range": "stddev: 0.0007525519342932648",
            "extra": "mean: 123.50890588889898 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 6.674822587888188,
            "unit": "iter/sec",
            "range": "stddev: 0.020921324153262998",
            "extra": "mean: 149.81671599999555 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 7.42858332014117,
            "unit": "iter/sec",
            "range": "stddev: 0.0007873084014149881",
            "extra": "mean: 134.6151691250057 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 7.037737630040518,
            "unit": "iter/sec",
            "range": "stddev: 0.0006713568536587511",
            "extra": "mean: 142.09111685714302 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 7.081001785152505,
            "unit": "iter/sec",
            "range": "stddev: 0.02016273507189803",
            "extra": "mean: 141.2229554999982 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 4.717559015252563,
            "unit": "iter/sec",
            "range": "stddev: 0.0015650468761860157",
            "extra": "mean: 211.97403080000754 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 5.131251654937628,
            "unit": "iter/sec",
            "range": "stddev: 0.02587523043733421",
            "extra": "mean: 194.88422460000265 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.91162397016213,
            "unit": "iter/sec",
            "range": "stddev: 0.0007186963462373643",
            "extra": "mean: 1.0969435125999951 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.4402772589491,
            "unit": "iter/sec",
            "range": "stddev: 0.019045322305962287",
            "extra": "mean: 694.3107612000006 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 5.047739822149603,
            "unit": "iter/sec",
            "range": "stddev: 0.0011477629207162555",
            "extra": "mean: 198.10846739999874 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.0504435014132785,
            "unit": "iter/sec",
            "range": "stddev: 0.023587569333694804",
            "extra": "mean: 198.0024130000004 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.9535508963055451,
            "unit": "iter/sec",
            "range": "stddev: 0.0011311938996603442",
            "extra": "mean: 1.0487117194000006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.107059388881979,
            "unit": "iter/sec",
            "range": "stddev: 0.0029510116533785656",
            "extra": "mean: 903.2939064000004 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 4.951582436618122,
            "unit": "iter/sec",
            "range": "stddev: 0.0007260642100072536",
            "extra": "mean: 201.9556400000056 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 5.255257675093812,
            "unit": "iter/sec",
            "range": "stddev: 0.0009216153314406197",
            "extra": "mean: 190.28562666665985 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 0.9377807292329758,
            "unit": "iter/sec",
            "range": "stddev: 0.0012901896988717165",
            "extra": "mean: 1.0663473548000013 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1207139531011145,
            "unit": "iter/sec",
            "range": "stddev: 0.002736439199117573",
            "extra": "mean: 892.2883463999995 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 0.1521171898476236,
            "unit": "iter/sec",
            "range": "stddev: 0.027656904766529492",
            "extra": "mean: 6.5738790008000025 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.7468567160019917,
            "unit": "iter/sec",
            "range": "stddev: 0.0025004952558755665",
            "extra": "mean: 266.8903765999971 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.1343483907230435,
            "unit": "iter/sec",
            "range": "stddev: 0.047313333815006416",
            "extra": "mean: 7.443334413000002 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.0848900761872682,
            "unit": "iter/sec",
            "range": "stddev: 0.027834894261742352",
            "extra": "mean: 921.7523710000137 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-True]",
            "value": 1.4109371482859712,
            "unit": "iter/sec",
            "range": "stddev: 0.007509363643763",
            "extra": "mean: 708.7487924000129 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.3419646517202615,
            "unit": "iter/sec",
            "range": "stddev: 0.0053949128196829595",
            "extra": "mean: 745.1761108000142 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-True]",
            "value": 0.5074004231461973,
            "unit": "iter/sec",
            "range": "stddev: 0.031714785660873414",
            "extra": "mean: 1.9708300473999998 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.4910770820787968,
            "unit": "iter/sec",
            "range": "stddev: 0.022186877046588963",
            "extra": "mean: 2.036340192800003 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-True]",
            "value": 1.5754199520716388,
            "unit": "iter/sec",
            "range": "stddev: 0.027839110192379272",
            "extra": "mean: 634.7513871999809 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.518190162179793,
            "unit": "iter/sec",
            "range": "stddev: 0.004313668204958033",
            "extra": "mean: 658.6790145999998 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-True]",
            "value": 0.5278208210408423,
            "unit": "iter/sec",
            "range": "stddev: 0.005841464220722755",
            "extra": "mean: 1.8945823282000105 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5099424939338645,
            "unit": "iter/sec",
            "range": "stddev: 0.025605502005956057",
            "extra": "mean: 1.9610054307999918 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-True]",
            "value": 1.5301554844298286,
            "unit": "iter/sec",
            "range": "stddev: 0.02717217021551475",
            "extra": "mean: 653.5283572000026 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.4767735196247733,
            "unit": "iter/sec",
            "range": "stddev: 0.01917313912885636",
            "extra": "mean: 677.1519036000086 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-True]",
            "value": 0.5322653949094912,
            "unit": "iter/sec",
            "range": "stddev: 0.007282989174497613",
            "extra": "mean: 1.8787620039999866 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5114049864612944,
            "unit": "iter/sec",
            "range": "stddev: 0.003813822083380172",
            "extra": "mean: 1.9553974374000063 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-True]",
            "value": 1.6561636653474738,
            "unit": "iter/sec",
            "range": "stddev: 0.02463309513653583",
            "extra": "mean: 603.8050591999877 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.3233414290518568,
            "unit": "iter/sec",
            "range": "stddev: 0.021786140517009292",
            "extra": "mean: 755.662883399998 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-True]",
            "value": 0.5422915387133852,
            "unit": "iter/sec",
            "range": "stddev: 0.029335961344757803",
            "extra": "mean: 1.8440265587999989 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.4903815456838413,
            "unit": "iter/sec",
            "range": "stddev: 0.0027443993053108857",
            "extra": "mean: 2.039228451400004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 0.47664223170560815,
            "unit": "iter/sec",
            "range": "stddev: 0.03015718715224276",
            "extra": "mean: 2.0980096464000213 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.46697354157342097,
            "unit": "iter/sec",
            "range": "stddev: 0.026165068583818007",
            "extra": "mean: 2.141448949400001 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 0.44602225232491843,
            "unit": "iter/sec",
            "range": "stddev: 0.033766469753405234",
            "extra": "mean: 2.2420406039999987 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.44341970450287604,
            "unit": "iter/sec",
            "range": "stddev: 0.035076074053632396",
            "extra": "mean: 2.255199734800044 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46904669111647407,
            "unit": "iter/sec",
            "range": "stddev: 0.0318323178922221",
            "extra": "mean: 2.1319839131999743 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.5200273738374104,
            "unit": "iter/sec",
            "range": "stddev: 0.02661842033046629",
            "extra": "mean: 1.9229756938000264 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.4416825258350163,
            "unit": "iter/sec",
            "range": "stddev: 0.025142390209638592",
            "extra": "mean: 2.2640696461999825 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.48197478707452185,
            "unit": "iter/sec",
            "range": "stddev: 0.04193511221239038",
            "extra": "mean: 2.0747973271999856 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 0.4663630136045173,
            "unit": "iter/sec",
            "range": "stddev: 0.03543167380587582",
            "extra": "mean: 2.1442523759999856 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.5095799117062315,
            "unit": "iter/sec",
            "range": "stddev: 0.04530166256866776",
            "extra": "mean: 1.9624007482000025 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 0.4374401999835238,
            "unit": "iter/sec",
            "range": "stddev: 0.027475275639001432",
            "extra": "mean: 2.2860267529999874 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.47269659003630776,
            "unit": "iter/sec",
            "range": "stddev: 0.03619827231437111",
            "extra": "mean: 2.1155219247999866 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 0.5729775998023922,
            "unit": "iter/sec",
            "range": "stddev: 0.03354535183439036",
            "extra": "mean: 1.7452689256000213 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.5455603840698622,
            "unit": "iter/sec",
            "range": "stddev: 0.04123811233387719",
            "extra": "mean: 1.8329776670000002 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 0.544693002581542,
            "unit": "iter/sec",
            "range": "stddev: 0.033900215644258304",
            "extra": "mean: 1.835896542200021 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5048656073032047,
            "unit": "iter/sec",
            "range": "stddev: 0.03221061412444713",
            "extra": "mean: 1.9807251385999733 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 3.04864883822537,
            "unit": "iter/sec",
            "range": "stddev: 0.004982817212772227",
            "extra": "mean: 328.01416399997834 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.9069965895636765,
            "unit": "iter/sec",
            "range": "stddev: 0.003705426640436518",
            "extra": "mean: 203.79064500000368 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.6675428893376062,
            "unit": "iter/sec",
            "range": "stddev: 0.02350132466823833",
            "extra": "mean: 1.4980310867999607 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 0.9872994842853368,
            "unit": "iter/sec",
            "range": "stddev: 0.001721292450500747",
            "extra": "mean: 1.0128638938000223 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 3.7514630208714985,
            "unit": "iter/sec",
            "range": "stddev: 0.023956830369399253",
            "extra": "mean: 266.5626701999827 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.767734548065028,
            "unit": "iter/sec",
            "range": "stddev: 0.0011612886575130216",
            "extra": "mean: 147.75993249999905 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.6123882112479782,
            "unit": "iter/sec",
            "range": "stddev: 0.026883940148107452",
            "extra": "mean: 1.6329510948000006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0142535008062739,
            "unit": "iter/sec",
            "range": "stddev: 0.0012666387554869792",
            "extra": "mean: 985.9468064000339 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 3.797892033804848,
            "unit": "iter/sec",
            "range": "stddev: 0.0020990197768453282",
            "extra": "mean: 263.30395679999583 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 6.579152187817294,
            "unit": "iter/sec",
            "range": "stddev: 0.0013993162011400246",
            "extra": "mean: 151.99526799998844 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 0.601319293736714,
            "unit": "iter/sec",
            "range": "stddev: 0.006967534551993314",
            "extra": "mean: 1.6630100022000078 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.0219736943169915,
            "unit": "iter/sec",
            "range": "stddev: 0.0005910034763698883",
            "extra": "mean: 978.4987671999943 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 1.466264862352757,
            "unit": "iter/sec",
            "range": "stddev: 0.02986891469939217",
            "extra": "mean: 682.0050222000191 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.550123199803068,
            "unit": "iter/sec",
            "range": "stddev: 0.0025604053732488723",
            "extra": "mean: 180.17618060000586 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.1393911549000091,
            "unit": "iter/sec",
            "range": "stddev: 0.025725327686233073",
            "extra": "mean: 7.174056350399996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.0398929228246918,
            "unit": "iter/sec",
            "range": "stddev: 0.02332830662483164",
            "extra": "mean: 961.6374706000215 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "63ab7fa6d20e04172c0d7590de0775e0606c7848",
          "message": "fix: 🐛 Skip building py3.14 package",
          "timestamp": "2026-01-14T16:46:21+08:00",
          "tree_id": "d86c915ea4f19260d03e57457aad6f3c4a9a585c",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/63ab7fa6d20e04172c0d7590de0775e0606c7848"
        },
        "date": 1768381525212,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.48494744013121116,
            "unit": "iter/sec",
            "range": "stddev: 0.026439824481019024",
            "extra": "mean: 2.062079139399998 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.457437095169272,
            "unit": "iter/sec",
            "range": "stddev: 0.017979440521940667",
            "extra": "mean: 105.7368915000012 msec\nrounds: 8"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-False]",
            "value": 78.73162760773124,
            "unit": "iter/sec",
            "range": "stddev: 0.00017839338757101727",
            "extra": "mean: 12.701375932202913 msec\nrounds: 59"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-False]",
            "value": 17.389827962233106,
            "unit": "iter/sec",
            "range": "stddev: 0.0005225075528338274",
            "extra": "mean: 57.50488171428612 msec\nrounds: 14"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-True]",
            "value": 25.90992999481387,
            "unit": "iter/sec",
            "range": "stddev: 0.000440263640310568",
            "extra": "mean: 38.595241291665396 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 25.81525428768436,
            "unit": "iter/sec",
            "range": "stddev: 0.0006211404465762555",
            "extra": "mean: 38.73678674073989 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-True]",
            "value": 25.285989353653125,
            "unit": "iter/sec",
            "range": "stddev: 0.0033013623691333953",
            "extra": "mean: 39.54759238461546 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 25.743067861636764,
            "unit": "iter/sec",
            "range": "stddev: 0.0004481181774305282",
            "extra": "mean: 38.84540899999862 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-True]",
            "value": 24.50913377497215,
            "unit": "iter/sec",
            "range": "stddev: 0.0005036501735101737",
            "extra": "mean: 40.801115583332624 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 27.488239838879867,
            "unit": "iter/sec",
            "range": "stddev: 0.0004099004462492173",
            "extra": "mean: 36.379193642860386 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-True]",
            "value": 24.4249829957672,
            "unit": "iter/sec",
            "range": "stddev: 0.0005126951382298592",
            "extra": "mean: 40.94168663999881 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 27.475362001462283,
            "unit": "iter/sec",
            "range": "stddev: 0.0022969955580798467",
            "extra": "mean: 36.396244749997415 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-True]",
            "value": 24.857498106027222,
            "unit": "iter/sec",
            "range": "stddev: 0.00039813683369502957",
            "extra": "mean: 40.22931011538643 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 26.460608047285206,
            "unit": "iter/sec",
            "range": "stddev: 0.008713983434172986",
            "extra": "mean: 37.79202648000364 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-True]",
            "value": 24.69738169779296,
            "unit": "iter/sec",
            "range": "stddev: 0.0004913457814113744",
            "extra": "mean: 40.49012208000022 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 27.53944261672981,
            "unit": "iter/sec",
            "range": "stddev: 0.0005140914554019237",
            "extra": "mean: 36.31155553571424 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 19.58296375986257,
            "unit": "iter/sec",
            "range": "stddev: 0.0005124931117402551",
            "extra": "mean: 51.06479347368296 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 19.574429356057173,
            "unit": "iter/sec",
            "range": "stddev: 0.0006104188956196711",
            "extra": "mean: 51.087057599998786 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 19.706646175303703,
            "unit": "iter/sec",
            "range": "stddev: 0.0008007736719916226",
            "extra": "mean: 50.7443017499952 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 19.733118959044855,
            "unit": "iter/sec",
            "range": "stddev: 0.00054366683853196",
            "extra": "mean: 50.67622619999668 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 6.632809786011159,
            "unit": "iter/sec",
            "range": "stddev: 0.0012175626060946716",
            "extra": "mean: 150.76566828571458 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 5.931753931283969,
            "unit": "iter/sec",
            "range": "stddev: 0.02157518642751299",
            "extra": "mean: 168.58420150000106 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 6.708898261143091,
            "unit": "iter/sec",
            "range": "stddev: 0.001220522331658467",
            "extra": "mean: 149.05577057142847 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 5.997863074489014,
            "unit": "iter/sec",
            "range": "stddev: 0.006159033413818889",
            "extra": "mean: 166.7260468571458 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 7.12578379397187,
            "unit": "iter/sec",
            "range": "stddev: 0.0007234915181522248",
            "extra": "mean: 140.3354394285665 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 6.71750066198338,
            "unit": "iter/sec",
            "range": "stddev: 0.018957807352246017",
            "extra": "mean: 148.86489042856965 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 7.133024198942833,
            "unit": "iter/sec",
            "range": "stddev: 0.0013744643423661965",
            "extra": "mean: 140.19299137499175 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 7.01856456210547,
            "unit": "iter/sec",
            "range": "stddev: 0.0007838504638154559",
            "extra": "mean: 142.47927637499913 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 6.892247907464716,
            "unit": "iter/sec",
            "range": "stddev: 0.017583740705725177",
            "extra": "mean: 145.090544250003 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 7.037705187318833,
            "unit": "iter/sec",
            "range": "stddev: 0.0003667170454231318",
            "extra": "mean: 142.09177187499833 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 7.0799564957202845,
            "unit": "iter/sec",
            "range": "stddev: 0.000635436228406656",
            "extra": "mean: 141.24380575000473 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.053280828992717,
            "unit": "iter/sec",
            "range": "stddev: 0.0005986671787381991",
            "extra": "mean: 141.77799300000515 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 6.1647230611462325,
            "unit": "iter/sec",
            "range": "stddev: 0.001041020436293801",
            "extra": "mean: 162.21328842857474 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 6.563060948921443,
            "unit": "iter/sec",
            "range": "stddev: 0.002221586688382635",
            "extra": "mean: 152.36792828570904 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 6.185587494715779,
            "unit": "iter/sec",
            "range": "stddev: 0.0015073864835971251",
            "extra": "mean: 161.6661312857153 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 6.5086426317562704,
            "unit": "iter/sec",
            "range": "stddev: 0.0011474600827828215",
            "extra": "mean: 153.64186614285862 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 4.0967092252374835,
            "unit": "iter/sec",
            "range": "stddev: 0.027079999191655598",
            "extra": "mean: 244.0983592000066 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 5.039547470811101,
            "unit": "iter/sec",
            "range": "stddev: 0.0018853136686181472",
            "extra": "mean: 198.43051500000115 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.9618285616104,
            "unit": "iter/sec",
            "range": "stddev: 0.024673801377852404",
            "extra": "mean: 1.0396863224000015 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.534846100795762,
            "unit": "iter/sec",
            "range": "stddev: 0.0022955965914524504",
            "extra": "mean: 651.5311205999978 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.728182235937404,
            "unit": "iter/sec",
            "range": "stddev: 0.001419996754077661",
            "extra": "mean: 211.4977701999976 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.009720701738696,
            "unit": "iter/sec",
            "range": "stddev: 0.0016021708157378915",
            "extra": "mean: 199.6119263999958 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.0175677789758009,
            "unit": "iter/sec",
            "range": "stddev: 0.003924278565640291",
            "extra": "mean: 982.7355195999985 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.1792183776497465,
            "unit": "iter/sec",
            "range": "stddev: 0.0020868670398710458",
            "extra": "mean: 848.0193482000004 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 4.6708245593334325,
            "unit": "iter/sec",
            "range": "stddev: 0.0015268931731206462",
            "extra": "mean: 214.09496059999924 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 4.627590700312581,
            "unit": "iter/sec",
            "range": "stddev: 0.025105014184687798",
            "extra": "mean: 216.0951702000034 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 1.001985316271117,
            "unit": "iter/sec",
            "range": "stddev: 0.002492628011388639",
            "extra": "mean: 998.0186173999982 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1833091517797207,
            "unit": "iter/sec",
            "range": "stddev: 0.02059655084830387",
            "extra": "mean: 845.0876919999985 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 0.15005923873411553,
            "unit": "iter/sec",
            "range": "stddev: 0.1053903198135205",
            "extra": "mean: 6.664034873399987 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.672061298530092,
            "unit": "iter/sec",
            "range": "stddev: 0.0006706516574001495",
            "extra": "mean: 272.3266085999967 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.13285579353912336,
            "unit": "iter/sec",
            "range": "stddev: 0.07846420640152353",
            "extra": "mean: 7.526958165399992 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1493440720620065,
            "unit": "iter/sec",
            "range": "stddev: 0.020572156931701734",
            "extra": "mean: 870.06147620001 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-True]",
            "value": 1.3302329367250532,
            "unit": "iter/sec",
            "range": "stddev: 0.03261355520225367",
            "extra": "mean: 751.7480378000073 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.2950407831795878,
            "unit": "iter/sec",
            "range": "stddev: 0.012575048895358024",
            "extra": "mean: 772.176454199996 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-True]",
            "value": 0.5388151722261678,
            "unit": "iter/sec",
            "range": "stddev: 0.010344781817150445",
            "extra": "mean: 1.8559239819999902 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.5165636691692511,
            "unit": "iter/sec",
            "range": "stddev: 0.02285847710153285",
            "extra": "mean: 1.935869786600017 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-True]",
            "value": 1.4900503322492553,
            "unit": "iter/sec",
            "range": "stddev: 0.026025647596330075",
            "extra": "mean: 671.1182691999966 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.452355647414427,
            "unit": "iter/sec",
            "range": "stddev: 0.020512643086012756",
            "extra": "mean: 688.5365866000257 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-True]",
            "value": 0.5567654496868004,
            "unit": "iter/sec",
            "range": "stddev: 0.021245936266746993",
            "extra": "mean: 1.7960884616000043 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5419889351302565,
            "unit": "iter/sec",
            "range": "stddev: 0.006981336403249711",
            "extra": "mean: 1.8450561168000035 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-True]",
            "value": 1.5042381941203837,
            "unit": "iter/sec",
            "range": "stddev: 0.00447721768906053",
            "extra": "mean: 664.7883320000119 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.4249017882096788,
            "unit": "iter/sec",
            "range": "stddev: 0.024071745990018777",
            "extra": "mean: 701.8027545999871 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-True]",
            "value": 0.554673166444575,
            "unit": "iter/sec",
            "range": "stddev: 0.03658488071890075",
            "extra": "mean: 1.8028634887999828 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5347916039918063,
            "unit": "iter/sec",
            "range": "stddev: 0.021332690251868073",
            "extra": "mean: 1.8698872468000105 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-True]",
            "value": 1.5841615618295946,
            "unit": "iter/sec",
            "range": "stddev: 0.010387661298271124",
            "extra": "mean: 631.2487464000014 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.3108243810422997,
            "unit": "iter/sec",
            "range": "stddev: 0.0020660199537035043",
            "extra": "mean: 762.8787001999854 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-True]",
            "value": 0.5727485219775643,
            "unit": "iter/sec",
            "range": "stddev: 0.022110583860051127",
            "extra": "mean: 1.7459669673999998 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.5151570229262883,
            "unit": "iter/sec",
            "range": "stddev: 0.018125978965533755",
            "extra": "mean: 1.9411557165999966 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 0.46302510672009706,
            "unit": "iter/sec",
            "range": "stddev: 0.03541100351666456",
            "extra": "mean: 2.1597101010000075 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.46294053546580305,
            "unit": "iter/sec",
            "range": "stddev: 0.021797756307947155",
            "extra": "mean: 2.1601046428000017 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 0.45768208371637165,
            "unit": "iter/sec",
            "range": "stddev: 0.029737098245619407",
            "extra": "mean: 2.1849227565999856 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.4571993828291835,
            "unit": "iter/sec",
            "range": "stddev: 0.03662601105088301",
            "extra": "mean: 2.1872295492000147 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46354620409350783,
            "unit": "iter/sec",
            "range": "stddev: 0.02870527822175572",
            "extra": "mean: 2.157282254000029 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.5039848718522396,
            "unit": "iter/sec",
            "range": "stddev: 0.037356026684532494",
            "extra": "mean: 1.984186541799977 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.4562529958581205,
            "unit": "iter/sec",
            "range": "stddev: 0.02209649816397457",
            "extra": "mean: 2.191766430199982 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.4984906395339938,
            "unit": "iter/sec",
            "range": "stddev: 0.027079817494059282",
            "extra": "mean: 2.006055722399992 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 0.4643335555370887,
            "unit": "iter/sec",
            "range": "stddev: 0.027338658657999244",
            "extra": "mean: 2.153624238600014 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.5097992600801418,
            "unit": "iter/sec",
            "range": "stddev: 0.029408190850439525",
            "extra": "mean: 1.9615563974000225 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 0.453279207952101,
            "unit": "iter/sec",
            "range": "stddev: 0.031137864964427536",
            "extra": "mean: 2.2061457539999765 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.49317239082931436,
            "unit": "iter/sec",
            "range": "stddev: 0.03371525173182315",
            "extra": "mean: 2.027688529599982 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 0.5585600589877535,
            "unit": "iter/sec",
            "range": "stddev: 0.030408151620129525",
            "extra": "mean: 1.7903177713999867 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.530799690356682,
            "unit": "iter/sec",
            "range": "stddev: 0.029881046014354457",
            "extra": "mean: 1.883949855600008 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 0.5579468812960857,
            "unit": "iter/sec",
            "range": "stddev: 0.029642986365703484",
            "extra": "mean: 1.7922853115999942 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5112067493533609,
            "unit": "iter/sec",
            "range": "stddev: 0.0348294807329885",
            "extra": "mean: 1.956155706599975 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 2.8005380523652383,
            "unit": "iter/sec",
            "range": "stddev: 0.002259864082578695",
            "extra": "mean: 357.0742411999845 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.504244358015904,
            "unit": "iter/sec",
            "range": "stddev: 0.0029058749966450756",
            "extra": "mean: 222.01282180003545 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.7136239662961379,
            "unit": "iter/sec",
            "range": "stddev: 0.009379895989297074",
            "extra": "mean: 1.4012982287999876 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.0344709372575498,
            "unit": "iter/sec",
            "range": "stddev: 0.0232291182073457",
            "extra": "mean: 966.6777132000107 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 3.508367706776207,
            "unit": "iter/sec",
            "range": "stddev: 0.0025996170616404304",
            "extra": "mean: 285.03283680001914 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.5302244699044465,
            "unit": "iter/sec",
            "range": "stddev: 0.03019935630298331",
            "extra": "mean: 180.82448649996272 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.6628212850316109,
            "unit": "iter/sec",
            "range": "stddev: 0.00146840592931326",
            "extra": "mean: 1.5087023042000056 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0869270206495039,
            "unit": "iter/sec",
            "range": "stddev: 0.0034029641886209653",
            "extra": "mean: 920.0249703999816 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 3.696185227621701,
            "unit": "iter/sec",
            "range": "stddev: 0.0022290906872162275",
            "extra": "mean: 270.5492118000393 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 5.844675566748913,
            "unit": "iter/sec",
            "range": "stddev: 0.002171146445294029",
            "extra": "mean: 171.09589550002133 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 0.6455205800808678,
            "unit": "iter/sec",
            "range": "stddev: 0.0036343624462328687",
            "extra": "mean: 1.5491372867999416 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.0951196138090726,
            "unit": "iter/sec",
            "range": "stddev: 0.0016729019881505508",
            "extra": "mean: 913.1422607999639 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 1.503975967416976,
            "unit": "iter/sec",
            "range": "stddev: 0.02396821605721651",
            "extra": "mean: 664.9042415999929 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.028846969844157,
            "unit": "iter/sec",
            "range": "stddev: 0.025542092292105127",
            "extra": "mean: 198.85274020000452 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.14900789597701422,
            "unit": "iter/sec",
            "range": "stddev: 0.023096184163676894",
            "extra": "mean: 6.711053756199999 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1266982982872635,
            "unit": "iter/sec",
            "range": "stddev: 0.002706534527764971",
            "extra": "mean: 887.5490461999789 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "08263f2e7a8c02dc0a638e9a5f2710448940d8df",
          "message": "fix: 🐛 Update type hints and improve formatting in load_qiskit.py, test_Feynman.py, test_MQT.py, and test_WMC.py",
          "timestamp": "2026-01-15T10:51:35+08:00",
          "tree_id": "1a52cdcc63460ce818b05f6a08c2ff125e8461ff",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/08263f2e7a8c02dc0a638e9a5f2710448940d8df"
        },
        "date": 1768446320040,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.488504273859312,
            "unit": "iter/sec",
            "range": "stddev: 0.02783445506691232",
            "extra": "mean: 2.047064997199999 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.776026051014364,
            "unit": "iter/sec",
            "range": "stddev: 0.015022484606022289",
            "extra": "mean: 102.2910531111197 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-False]",
            "value": 77.839015006213,
            "unit": "iter/sec",
            "range": "stddev: 0.000245129571315249",
            "extra": "mean: 12.847027932203167 msec\nrounds: 59"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-False]",
            "value": 17.1427026416256,
            "unit": "iter/sec",
            "range": "stddev: 0.003950634134453399",
            "extra": "mean: 58.33385907142891 msec\nrounds: 14"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-True]",
            "value": 26.124878060092033,
            "unit": "iter/sec",
            "range": "stddev: 0.0009426179153717537",
            "extra": "mean: 38.27769062499797 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 26.148055229726452,
            "unit": "iter/sec",
            "range": "stddev: 0.000475271404305447",
            "extra": "mean: 38.24376196296039 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-True]",
            "value": 26.02627591995761,
            "unit": "iter/sec",
            "range": "stddev: 0.0005304537994041121",
            "extra": "mean: 38.422708000001435 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 25.155009852333922,
            "unit": "iter/sec",
            "range": "stddev: 0.0036169567900481915",
            "extra": "mean: 39.75351255556032 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-True]",
            "value": 24.740818458830837,
            "unit": "iter/sec",
            "range": "stddev: 0.00035194387573821617",
            "extra": "mean: 40.419034708331004 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 27.7412229798918,
            "unit": "iter/sec",
            "range": "stddev: 0.0004898702184100172",
            "extra": "mean: 36.04743744444321 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-True]",
            "value": 24.874282006359326,
            "unit": "iter/sec",
            "range": "stddev: 0.0004162215437925068",
            "extra": "mean: 40.202165423080004 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 27.908133595635196,
            "unit": "iter/sec",
            "range": "stddev: 0.00045974220914099566",
            "extra": "mean: 35.83184796551207 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-True]",
            "value": 24.261701315937803,
            "unit": "iter/sec",
            "range": "stddev: 0.0010600179884193803",
            "extra": "mean: 41.21722491666683 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 27.100131435537484,
            "unit": "iter/sec",
            "range": "stddev: 0.0006245266478422123",
            "extra": "mean: 36.900190037036495 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-True]",
            "value": 23.282881201715455,
            "unit": "iter/sec",
            "range": "stddev: 0.009946192119841617",
            "extra": "mean: 42.95001083999523 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 27.02406893294455,
            "unit": "iter/sec",
            "range": "stddev: 0.0004873216310885052",
            "extra": "mean: 37.00405007407741 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 19.47988760482615,
            "unit": "iter/sec",
            "range": "stddev: 0.0005660043094847855",
            "extra": "mean: 51.334998450003866 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 19.559948704386695,
            "unit": "iter/sec",
            "range": "stddev: 0.0006244548007841117",
            "extra": "mean: 51.124878449999756 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 19.640557971792678,
            "unit": "iter/sec",
            "range": "stddev: 0.0006598798069582841",
            "extra": "mean: 50.91505045000133 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 19.718491499788236,
            "unit": "iter/sec",
            "range": "stddev: 0.0007051248847099192",
            "extra": "mean: 50.71381855000112 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 6.519225897990282,
            "unit": "iter/sec",
            "range": "stddev: 0.002001161938675167",
            "extra": "mean: 153.39244499999236 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 6.140139347597271,
            "unit": "iter/sec",
            "range": "stddev: 0.0017469395195910899",
            "extra": "mean: 162.86275333332867 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 6.714721285785054,
            "unit": "iter/sec",
            "range": "stddev: 0.0027448340486079495",
            "extra": "mean: 148.92650900000604 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 6.331166338198646,
            "unit": "iter/sec",
            "range": "stddev: 0.0006783789964882059",
            "extra": "mean: 157.94878014285783 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 7.22293543543226,
            "unit": "iter/sec",
            "range": "stddev: 0.0006364964327847505",
            "extra": "mean: 138.44786637500306 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 6.764630983108348,
            "unit": "iter/sec",
            "range": "stddev: 0.020259560579782707",
            "extra": "mean: 147.82772371428013 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 7.26818474976304,
            "unit": "iter/sec",
            "range": "stddev: 0.0005146307334928098",
            "extra": "mean: 137.58593574999622 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 7.146871904530659,
            "unit": "iter/sec",
            "range": "stddev: 0.000498549079010602",
            "extra": "mean: 139.9213548749998 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 6.848876998370526,
            "unit": "iter/sec",
            "range": "stddev: 0.020767887283854095",
            "extra": "mean: 146.00933850000786 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 7.0788484185211615,
            "unit": "iter/sec",
            "range": "stddev: 0.0014772708338796935",
            "extra": "mean: 141.26591514286295 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 7.314953553661707,
            "unit": "iter/sec",
            "range": "stddev: 0.00036790272863299934",
            "extra": "mean: 136.70626787499174 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 6.865284077804981,
            "unit": "iter/sec",
            "range": "stddev: 0.015316718232055581",
            "extra": "mean: 145.66039637499273 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 6.225504463121178,
            "unit": "iter/sec",
            "range": "stddev: 0.0013574609810531632",
            "extra": "mean: 160.62955314285432 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 6.705661634567053,
            "unit": "iter/sec",
            "range": "stddev: 0.0008269648047164335",
            "extra": "mean: 149.12771542857075 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 6.285943739081214,
            "unit": "iter/sec",
            "range": "stddev: 0.00038537455555229916",
            "extra": "mean: 159.08510185714218 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 6.693720133457703,
            "unit": "iter/sec",
            "range": "stddev: 0.0005185718581839448",
            "extra": "mean: 149.39375714285217 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 4.314255503083175,
            "unit": "iter/sec",
            "range": "stddev: 0.020545946133646933",
            "extra": "mean: 231.7897025999855 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 5.134020346167354,
            "unit": "iter/sec",
            "range": "stddev: 0.0009493848434053005",
            "extra": "mean: 194.77912680001737 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.9675539845018685,
            "unit": "iter/sec",
            "range": "stddev: 0.020428871189687108",
            "extra": "mean: 1.0335340621999876 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.542002115284569,
            "unit": "iter/sec",
            "range": "stddev: 0.004823043981598734",
            "extra": "mean: 648.5075410000036 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.864824105001711,
            "unit": "iter/sec",
            "range": "stddev: 0.0010202994649394486",
            "extra": "mean: 205.55727780000552 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.126260787437028,
            "unit": "iter/sec",
            "range": "stddev: 0.00178203937110256",
            "extra": "mean: 195.07396159998507 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.0227005452852955,
            "unit": "iter/sec",
            "range": "stddev: 0.0008537507573547163",
            "extra": "mean: 977.803331199982 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.1844454583918627,
            "unit": "iter/sec",
            "range": "stddev: 0.002400224677569246",
            "extra": "mean: 844.2769508000083 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 4.751980327926991,
            "unit": "iter/sec",
            "range": "stddev: 0.0013552776418866606",
            "extra": "mean: 210.43858159998763 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 4.8135536655366575,
            "unit": "iter/sec",
            "range": "stddev: 0.019960615454949784",
            "extra": "mean: 207.7467230000252 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 1.0059131615382595,
            "unit": "iter/sec",
            "range": "stddev: 0.0003725126268963393",
            "extra": "mean: 994.1215983999882 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1867874102183682,
            "unit": "iter/sec",
            "range": "stddev: 0.021021437092150555",
            "extra": "mean: 842.610893400024 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 0.1495304312241851,
            "unit": "iter/sec",
            "range": "stddev: 0.12981561593657162",
            "extra": "mean: 6.687601926999991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.5936435388716816,
            "unit": "iter/sec",
            "range": "stddev: 0.002469444487242912",
            "extra": "mean: 278.2691129999989 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.13300779960966336,
            "unit": "iter/sec",
            "range": "stddev: 0.07446797192417286",
            "extra": "mean: 7.518356088400003 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1606105388211174,
            "unit": "iter/sec",
            "range": "stddev: 0.02424635814260432",
            "extra": "mean: 861.6154744000028 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-True]",
            "value": 1.3630093571522084,
            "unit": "iter/sec",
            "range": "stddev: 0.022585247834435745",
            "extra": "mean: 733.6706785999922 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.3163256914250343,
            "unit": "iter/sec",
            "range": "stddev: 0.0020849759213238043",
            "extra": "mean: 759.6904068000185 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-True]",
            "value": 0.5431471107474058,
            "unit": "iter/sec",
            "range": "stddev: 0.006264879400025468",
            "extra": "mean: 1.8411218254000006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.5242730697204198,
            "unit": "iter/sec",
            "range": "stddev: 0.0028963464029990098",
            "extra": "mean: 1.9074029504000123 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-True]",
            "value": 1.5184147439587816,
            "unit": "iter/sec",
            "range": "stddev: 0.029578958831272137",
            "extra": "mean: 658.5815923999917 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4762718306066354,
            "unit": "iter/sec",
            "range": "stddev: 0.024841718524648174",
            "extra": "mean: 677.3820236000006 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-True]",
            "value": 0.5635235204161476,
            "unit": "iter/sec",
            "range": "stddev: 0.002844231804461418",
            "extra": "mean: 1.774548823200007 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5465594126240568,
            "unit": "iter/sec",
            "range": "stddev: 0.003661394354503183",
            "extra": "mean: 1.8296272589999945 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-True]",
            "value": 1.5336895756601292,
            "unit": "iter/sec",
            "range": "stddev: 0.0006532134917473654",
            "extra": "mean: 652.0224274000043 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.456307338163938,
            "unit": "iter/sec",
            "range": "stddev: 0.02059918485245982",
            "extra": "mean: 686.6682422000054 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-True]",
            "value": 0.5626273734220474,
            "unit": "iter/sec",
            "range": "stddev: 0.0306153996025274",
            "extra": "mean: 1.7773753060000217 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5405484141979576,
            "unit": "iter/sec",
            "range": "stddev: 0.02287438092098527",
            "extra": "mean: 1.84997305280001 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-True]",
            "value": 1.572086404561476,
            "unit": "iter/sec",
            "range": "stddev: 0.006752296266287408",
            "extra": "mean: 636.0973525999952 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.3225314137673303,
            "unit": "iter/sec",
            "range": "stddev: 0.004746782450517011",
            "extra": "mean: 756.1257067999804 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-True]",
            "value": 0.5762153122091344,
            "unit": "iter/sec",
            "range": "stddev: 0.02447782354899435",
            "extra": "mean: 1.735462385000028 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.5199521634692076,
            "unit": "iter/sec",
            "range": "stddev: 0.01614633543966491",
            "extra": "mean: 1.923253849599996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-True]",
            "value": 0.47491493401113727,
            "unit": "iter/sec",
            "range": "stddev: 0.028738384768890145",
            "extra": "mean: 2.1056402491999733 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.45615050286034753,
            "unit": "iter/sec",
            "range": "stddev: 0.02803113635273781",
            "extra": "mean: 2.1922589008000157 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-True]",
            "value": 0.45831603510739993,
            "unit": "iter/sec",
            "range": "stddev: 0.01829617635297017",
            "extra": "mean: 2.181900530200005 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.4557508934511334,
            "unit": "iter/sec",
            "range": "stddev: 0.03659353490757032",
            "extra": "mean: 2.1941811072000066 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46397978436961634,
            "unit": "iter/sec",
            "range": "stddev: 0.035390640606308116",
            "extra": "mean: 2.1552663147999964 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.5089397790940889,
            "unit": "iter/sec",
            "range": "stddev: 0.042047888083621664",
            "extra": "mean: 1.964869010199982 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.45286441873539574,
            "unit": "iter/sec",
            "range": "stddev: 0.02845896300169236",
            "extra": "mean: 2.2081664150000053 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.4907438046642351,
            "unit": "iter/sec",
            "range": "stddev: 0.036229841284702975",
            "extra": "mean: 2.0377231266000306 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-True]",
            "value": 0.4608904706384358,
            "unit": "iter/sec",
            "range": "stddev: 0.022618921248231203",
            "extra": "mean: 2.169712900800005 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.5108158782520422,
            "unit": "iter/sec",
            "range": "stddev: 0.01878213025762276",
            "extra": "mean: 1.9576525370000126 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-True]",
            "value": 0.4473531956032373,
            "unit": "iter/sec",
            "range": "stddev: 0.035852016535558445",
            "extra": "mean: 2.2353701947999753 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.49271863573223473,
            "unit": "iter/sec",
            "range": "stddev: 0.0507309020420705",
            "extra": "mean: 2.0295558711999773 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-True]",
            "value": 0.5643436842712058,
            "unit": "iter/sec",
            "range": "stddev: 0.03267316677038609",
            "extra": "mean: 1.7719698613999753 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.5362976836845806,
            "unit": "iter/sec",
            "range": "stddev: 0.030589374786875755",
            "extra": "mean: 1.8646360601999958 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-True]",
            "value": 0.5585282839324466,
            "unit": "iter/sec",
            "range": "stddev: 0.028405566144110796",
            "extra": "mean: 1.7904196238000167 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5221729516140117,
            "unit": "iter/sec",
            "range": "stddev: 0.037298904618039995",
            "extra": "mean: 1.9150743003999877 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-True]",
            "value": 2.9916768934099434,
            "unit": "iter/sec",
            "range": "stddev: 0.0016866349620513366",
            "extra": "mean: 334.2606958000033 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.274968300340496,
            "unit": "iter/sec",
            "range": "stddev: 0.03842467314709589",
            "extra": "mean: 233.91986320000342 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-True]",
            "value": 0.7188071470955089,
            "unit": "iter/sec",
            "range": "stddev: 0.0035759047561079132",
            "extra": "mean: 1.3911937353999746 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.0520252830450785,
            "unit": "iter/sec",
            "range": "stddev: 0.0012680726997493538",
            "extra": "mean: 950.5474973999753 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 3.842080268727011,
            "unit": "iter/sec",
            "range": "stddev: 0.0015220249485839218",
            "extra": "mean: 260.27566580000894 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.4426335139407644,
            "unit": "iter/sec",
            "range": "stddev: 0.0006081413637781863",
            "extra": "mean: 155.21603049997643 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 0.6620814549195327,
            "unit": "iter/sec",
            "range": "stddev: 0.01843003644168809",
            "extra": "mean: 1.5103881743999863 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0891986587253004,
            "unit": "iter/sec",
            "range": "stddev: 0.004230579555729973",
            "extra": "mean: 918.1061618000058 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-True]",
            "value": 3.5884976732888134,
            "unit": "iter/sec",
            "range": "stddev: 0.03244535534469108",
            "extra": "mean: 278.66814779999913 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 6.331154679599235,
            "unit": "iter/sec",
            "range": "stddev: 0.0013821241269342073",
            "extra": "mean: 157.9490709999997 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-True]",
            "value": 0.6486503624600253,
            "unit": "iter/sec",
            "range": "stddev: 0.023430710055353857",
            "extra": "mean: 1.541662593400042 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.0985313349438064,
            "unit": "iter/sec",
            "range": "stddev: 0.0036142327397707475",
            "extra": "mean: 910.3063045999988 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-True]",
            "value": 1.4994136211664513,
            "unit": "iter/sec",
            "range": "stddev: 0.020607830834433134",
            "extra": "mean: 666.927381399978 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.329024355292969,
            "unit": "iter/sec",
            "range": "stddev: 0.0012274638797228341",
            "extra": "mean: 187.65161000001171 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-True]",
            "value": 0.14945916797096517,
            "unit": "iter/sec",
            "range": "stddev: 0.018236679980848373",
            "extra": "mean: 6.690790625799991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1325554190245848,
            "unit": "iter/sec",
            "range": "stddev: 0.0011078084142093058",
            "extra": "mean: 882.9589997999847 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "da8ff4b8e4146c3b0ad739da576c9498c7795d33",
          "message": "fix: 🐛 Refactor parameterization in test_Feynman.py and test_MQT.py for clarity",
          "timestamp": "2026-01-15T12:01:20+08:00",
          "tree_id": "fe53b638766485919226e3ed3dab061c725056f0",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/da8ff4b8e4146c3b0ad739da576c9498c7795d33"
        },
        "date": 1768450100405,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.49351603667608573,
            "unit": "iter/sec",
            "range": "stddev: 0.023360442135067598",
            "extra": "mean: 2.026276606400006 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.708217777990084,
            "unit": "iter/sec",
            "range": "stddev: 0.015830119544936166",
            "extra": "mean: 103.00551788889025 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 99.2795285969961,
            "unit": "iter/sec",
            "range": "stddev: 0.0001390276569388925",
            "extra": "mean: 10.072569986298838 msec\nrounds: 73"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.439276070931236,
            "unit": "iter/sec",
            "range": "stddev: 0.0004088366011830481",
            "extra": "mean: 60.82992923077987 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 26.050437630801138,
            "unit": "iter/sec",
            "range": "stddev: 0.00041526404287170303",
            "extra": "mean: 38.38707104166398 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 26.078635144226613,
            "unit": "iter/sec",
            "range": "stddev: 0.00045575478985730586",
            "extra": "mean: 38.345565037033154 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 27.74580148476212,
            "unit": "iter/sec",
            "range": "stddev: 0.0004861452274627866",
            "extra": "mean: 36.04148903570855 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 27.74208744941515,
            "unit": "iter/sec",
            "range": "stddev: 0.00043018024320371406",
            "extra": "mean: 36.046314172406724 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 27.564222642729725,
            "unit": "iter/sec",
            "range": "stddev: 0.0010656771926355244",
            "extra": "mean: 36.278911724135185 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 28.027358738069385,
            "unit": "iter/sec",
            "range": "stddev: 0.00046792256648625",
            "extra": "mean: 35.679423428569685 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 19.94636935895642,
            "unit": "iter/sec",
            "range": "stddev: 0.00045683000560942094",
            "extra": "mean: 50.134437100001605 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 19.747381152666975,
            "unit": "iter/sec",
            "range": "stddev: 0.00048820374457964234",
            "extra": "mean: 50.639626200000976 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 6.275113691333672,
            "unit": "iter/sec",
            "range": "stddev: 0.000843517480885851",
            "extra": "mean: 159.35966249998992 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 6.2300074887806245,
            "unit": "iter/sec",
            "range": "stddev: 0.004133799058792617",
            "extra": "mean: 160.51345071428256 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 6.986765264004982,
            "unit": "iter/sec",
            "range": "stddev: 0.0011399631985776265",
            "extra": "mean: 143.127751142848 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 6.721047270628922,
            "unit": "iter/sec",
            "range": "stddev: 0.020200910142970416",
            "extra": "mean: 148.7863363749895 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 7.028830268208134,
            "unit": "iter/sec",
            "range": "stddev: 0.0009604385981581546",
            "extra": "mean: 142.27118337500144 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.027115707057418,
            "unit": "iter/sec",
            "range": "stddev: 0.0003945517242103697",
            "extra": "mean: 142.30589642855713 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 6.62803870328775,
            "unit": "iter/sec",
            "range": "stddev: 0.001407682436465139",
            "extra": "mean: 150.87419442858163 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 6.5464138389144155,
            "unit": "iter/sec",
            "range": "stddev: 0.0017558337308164508",
            "extra": "mean: 152.75539014286161 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.7126435304983145,
            "unit": "iter/sec",
            "range": "stddev: 0.02844938004350051",
            "extra": "mean: 212.19512859998986 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.535274948232965,
            "unit": "iter/sec",
            "range": "stddev: 0.0014534250599756088",
            "extra": "mean: 651.3491287999955 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 4.870618900824958,
            "unit": "iter/sec",
            "range": "stddev: 0.006019419042336449",
            "extra": "mean: 205.31271700001525 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.1755390612106666,
            "unit": "iter/sec",
            "range": "stddev: 0.0022630501199323427",
            "extra": "mean: 850.6735616000014 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 4.885799245379996,
            "unit": "iter/sec",
            "range": "stddev: 0.0007909423705459413",
            "extra": "mean: 204.6748033999961 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1695818690853672,
            "unit": "iter/sec",
            "range": "stddev: 0.03072077764233568",
            "extra": "mean: 855.0064141999883 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.4995075153570716,
            "unit": "iter/sec",
            "range": "stddev: 0.0022869296513879363",
            "extra": "mean: 285.7544942000118 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.140286007202269,
            "unit": "iter/sec",
            "range": "stddev: 0.030963782409549268",
            "extra": "mean: 876.9729643999881 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.240018427030949,
            "unit": "iter/sec",
            "range": "stddev: 0.02034320947427281",
            "extra": "mean: 806.4396288000012 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.5119209785606764,
            "unit": "iter/sec",
            "range": "stddev: 0.02960402853856153",
            "extra": "mean: 1.9534264894000102 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.444121561199106,
            "unit": "iter/sec",
            "range": "stddev: 0.003432907782943341",
            "extra": "mean: 692.4624816000005 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.542049032819932,
            "unit": "iter/sec",
            "range": "stddev: 0.003772015531987097",
            "extra": "mean: 1.844851553000001 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.468150632413441,
            "unit": "iter/sec",
            "range": "stddev: 0.002744480625035901",
            "extra": "mean: 681.1290190000022 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5378267238145897,
            "unit": "iter/sec",
            "range": "stddev: 0.022448266875708268",
            "extra": "mean: 1.8593349042 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.2841552881733296,
            "unit": "iter/sec",
            "range": "stddev: 0.035746587106088586",
            "extra": "mean: 778.7220199999865 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.5177040052506271,
            "unit": "iter/sec",
            "range": "stddev: 0.025975356853808928",
            "extra": "mean: 1.9316056855999932 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.455049206634478,
            "unit": "iter/sec",
            "range": "stddev: 0.02931248784295489",
            "extra": "mean: 2.1975645389999725 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.4512149217788258,
            "unit": "iter/sec",
            "range": "stddev: 0.03131445783915397",
            "extra": "mean: 2.2162387627999918 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.4981313669761495,
            "unit": "iter/sec",
            "range": "stddev: 0.048232923221036214",
            "extra": "mean: 2.0075025712000185 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.4925398423088266,
            "unit": "iter/sec",
            "range": "stddev: 0.030332855024872225",
            "extra": "mean: 2.0302926059999664 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.5001504701188956,
            "unit": "iter/sec",
            "range": "stddev: 0.03320932144062327",
            "extra": "mean: 1.999398300599978 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.4903189039898101,
            "unit": "iter/sec",
            "range": "stddev: 0.03234554489554349",
            "extra": "mean: 2.0394889771999942 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.5277248539409032,
            "unit": "iter/sec",
            "range": "stddev: 0.02921528583635934",
            "extra": "mean: 1.8949268591999726 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5183310879007701,
            "unit": "iter/sec",
            "range": "stddev: 0.030500300118591415",
            "extra": "mean: 1.9292688078000082 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.393879043877258,
            "unit": "iter/sec",
            "range": "stddev: 0.027290027531400765",
            "extra": "mean: 227.58933280001656 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.0531612818235072,
            "unit": "iter/sec",
            "range": "stddev: 0.0008694051285720445",
            "extra": "mean: 949.52218359997 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.452790695130156,
            "unit": "iter/sec",
            "range": "stddev: 0.0013015782349511168",
            "extra": "mean: 154.9717087142913 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0933894072463604,
            "unit": "iter/sec",
            "range": "stddev: 0.0012957668953758293",
            "extra": "mean: 914.5872397999938 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 5.760122133021475,
            "unit": "iter/sec",
            "range": "stddev: 0.027986801654420152",
            "extra": "mean: 173.60743000000411 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1003754205841112,
            "unit": "iter/sec",
            "range": "stddev: 0.001845461029440251",
            "extra": "mean: 908.7807500000054 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.3487921318383975,
            "unit": "iter/sec",
            "range": "stddev: 0.001537734873224202",
            "extra": "mean: 186.95809733333135 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1278064935368564,
            "unit": "iter/sec",
            "range": "stddev: 0.0032509018815592935",
            "extra": "mean: 886.6769305999924 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "71eac6faedddeba87608f7131e5e3e289f4b378d",
          "message": "fix: 🐛 Reset signal alarm in test functions for proper resource management",
          "timestamp": "2026-01-15T12:55:10+08:00",
          "tree_id": "95527f62a10c28e07ac3dc8da6d649a294033d12",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/71eac6faedddeba87608f7131e5e3e289f4b378d"
        },
        "date": 1768453304726,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.49094040824945495,
            "unit": "iter/sec",
            "range": "stddev: 0.01778532957005492",
            "extra": "mean: 2.0369070933999867 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.485658049041902,
            "unit": "iter/sec",
            "range": "stddev: 0.01634112407959818",
            "extra": "mean: 105.42231175000083 msec\nrounds: 8"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 99.74848180916668,
            "unit": "iter/sec",
            "range": "stddev: 0.00011462089878226977",
            "extra": "mean: 10.02521523999879 msec\nrounds: 75"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.575870550631315,
            "unit": "iter/sec",
            "range": "stddev: 0.00019793456453833059",
            "extra": "mean: 60.32865646154033 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 26.033839735123436,
            "unit": "iter/sec",
            "range": "stddev: 0.00035672334873305093",
            "extra": "mean: 38.41154474999916 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 26.14693822960498,
            "unit": "iter/sec",
            "range": "stddev: 0.0004335302976541885",
            "extra": "mean: 38.24539574074282 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 27.61768755032593,
            "unit": "iter/sec",
            "range": "stddev: 0.0012470130959930964",
            "extra": "mean: 36.208679607145406 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 27.956290447855,
            "unit": "iter/sec",
            "range": "stddev: 0.00032705834850740764",
            "extra": "mean: 35.77012486206756 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 27.915397236838423,
            "unit": "iter/sec",
            "range": "stddev: 0.00039028940383203014",
            "extra": "mean: 35.82252444827669 msec\nrounds: 29"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 27.973061663958287,
            "unit": "iter/sec",
            "range": "stddev: 0.0004127935749203008",
            "extra": "mean: 35.748678925926924 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 19.98963329621448,
            "unit": "iter/sec",
            "range": "stddev: 0.000569379767898605",
            "extra": "mean: 50.025930199998925 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 19.994181912997476,
            "unit": "iter/sec",
            "range": "stddev: 0.0013916910318806657",
            "extra": "mean: 50.01454945000461 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 6.366630057270629,
            "unit": "iter/sec",
            "range": "stddev: 0.0006852972635340158",
            "extra": "mean: 157.0689659999971 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 6.285168576594062,
            "unit": "iter/sec",
            "range": "stddev: 0.0007617962453197186",
            "extra": "mean: 159.10472214285474 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 7.046536312321709,
            "unit": "iter/sec",
            "range": "stddev: 0.0009656985596950059",
            "extra": "mean: 141.91369428571323 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 6.776407703809774,
            "unit": "iter/sec",
            "range": "stddev: 0.016204630976435846",
            "extra": "mean: 147.57081387499582 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 7.124659553709402,
            "unit": "iter/sec",
            "range": "stddev: 0.00048695864512484635",
            "extra": "mean: 140.3575837499993 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.1390566278162595,
            "unit": "iter/sec",
            "range": "stddev: 0.0006947418296187945",
            "extra": "mean: 140.07452975000234 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 6.665318043243246,
            "unit": "iter/sec",
            "range": "stddev: 0.0013698206904237979",
            "extra": "mean: 150.0303501666688 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 6.683822492176481,
            "unit": "iter/sec",
            "range": "stddev: 0.0034334116439698878",
            "extra": "mean: 149.61498471428823 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.9556738316978866,
            "unit": "iter/sec",
            "range": "stddev: 0.019207114923301506",
            "extra": "mean: 201.78890579999802 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.551110727125001,
            "unit": "iter/sec",
            "range": "stddev: 0.0013379100605256696",
            "extra": "mean: 644.6993000000134 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.174667009065287,
            "unit": "iter/sec",
            "range": "stddev: 0.0022081515978388615",
            "extra": "mean: 193.24914980000472 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.1680120090621762,
            "unit": "iter/sec",
            "range": "stddev: 0.01886842810331817",
            "extra": "mean: 856.155580799998 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 5.140731601624185,
            "unit": "iter/sec",
            "range": "stddev: 0.000971655558583968",
            "extra": "mean: 194.5248415000028 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.191523639900376,
            "unit": "iter/sec",
            "range": "stddev: 0.01683206954208909",
            "extra": "mean: 839.2615694000085 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.6983749754577104,
            "unit": "iter/sec",
            "range": "stddev: 0.002061267143773968",
            "extra": "mean: 270.38902399999074 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1544651924687588,
            "unit": "iter/sec",
            "range": "stddev: 0.022905604870920148",
            "extra": "mean: 866.201949200007 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.2815696445191191,
            "unit": "iter/sec",
            "range": "stddev: 0.025252710412789616",
            "extra": "mean: 780.2931384000033 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.518010928611452,
            "unit": "iter/sec",
            "range": "stddev: 0.02020206110855406",
            "extra": "mean: 1.9304612021999958 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4919162295971558,
            "unit": "iter/sec",
            "range": "stddev: 0.0032715469099162653",
            "extra": "mean: 670.2789205999977 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5463677763844019,
            "unit": "iter/sec",
            "range": "stddev: 0.006444651884450662",
            "extra": "mean: 1.8302689931999965 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.4632094691956536,
            "unit": "iter/sec",
            "range": "stddev: 0.014668087101834395",
            "extra": "mean: 683.4291474000054 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5417674730198261,
            "unit": "iter/sec",
            "range": "stddev: 0.018718769998685793",
            "extra": "mean: 1.8458103333999987 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.3209155011088265,
            "unit": "iter/sec",
            "range": "stddev: 0.022389798496471307",
            "extra": "mean: 757.050696400006 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.5203888728830951,
            "unit": "iter/sec",
            "range": "stddev: 0.015037268743333438",
            "extra": "mean: 1.9216398583999876 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.4640796139700879,
            "unit": "iter/sec",
            "range": "stddev: 0.03592096406504847",
            "extra": "mean: 2.1548026887999754 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.45355498286439866,
            "unit": "iter/sec",
            "range": "stddev: 0.020185863823938163",
            "extra": "mean: 2.2048043517999987 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.5039170857826368,
            "unit": "iter/sec",
            "range": "stddev: 0.03868094008027378",
            "extra": "mean: 1.9844534511999996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.49223245001281896,
            "unit": "iter/sec",
            "range": "stddev: 0.04783962803766659",
            "extra": "mean: 2.0315604954000035 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.5101910931565639,
            "unit": "iter/sec",
            "range": "stddev: 0.02398430536973414",
            "extra": "mean: 1.9600498978000132 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.49287261480657224,
            "unit": "iter/sec",
            "range": "stddev: 0.033717357150815835",
            "extra": "mean: 2.028921814600005 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.5345423301008274,
            "unit": "iter/sec",
            "range": "stddev: 0.028367145120302174",
            "extra": "mean: 1.8707592340000019 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5226118093565226,
            "unit": "iter/sec",
            "range": "stddev: 0.027762982154323906",
            "extra": "mean: 1.913466136999989 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.701336317801656,
            "unit": "iter/sec",
            "range": "stddev: 0.0013461914946298228",
            "extra": "mean: 212.70548040000676 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.0535831905897963,
            "unit": "iter/sec",
            "range": "stddev: 0.003489608037738079",
            "extra": "mean: 949.1419461999953 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.40041276298488,
            "unit": "iter/sec",
            "range": "stddev: 0.0029526909254767282",
            "extra": "mean: 156.23992342857005 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.094036513153975,
            "unit": "iter/sec",
            "range": "stddev: 0.002075405995695527",
            "extra": "mean: 914.0462754000055 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 6.084234720819857,
            "unit": "iter/sec",
            "range": "stddev: 0.01790503581655583",
            "extra": "mean: 164.35920799999136 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1016662361186114,
            "unit": "iter/sec",
            "range": "stddev: 0.001167425493233368",
            "extra": "mean: 907.7159371999983 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.189908477961996,
            "unit": "iter/sec",
            "range": "stddev: 0.010060159862159527",
            "extra": "mean: 192.68162516667076 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1247239659422272,
            "unit": "iter/sec",
            "range": "stddev: 0.013161988353183397",
            "extra": "mean: 889.1070433999857 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "fa8dde504cfa5c0f7b708c72676d80942feacc6f",
          "message": "fix: 🐛 Refactor signal handling in benchmark tests for improved resource management",
          "timestamp": "2026-01-15T13:16:36+08:00",
          "tree_id": "67275e0ca73bbdbcc839760798edf4af5f35ecae",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/fa8dde504cfa5c0f7b708c72676d80942feacc6f"
        },
        "date": 1768454567315,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.49535671915515384,
            "unit": "iter/sec",
            "range": "stddev: 0.01948379604410675",
            "extra": "mean: 2.018747220599997 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.471225948846708,
            "unit": "iter/sec",
            "range": "stddev: 0.01873337778642332",
            "extra": "mean: 105.58295255555252 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 98.72249067031127,
            "unit": "iter/sec",
            "range": "stddev: 0.00014775506369969795",
            "extra": "mean: 10.129404082191872 msec\nrounds: 73"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.163207774998913,
            "unit": "iter/sec",
            "range": "stddev: 0.000832238754470411",
            "extra": "mean: 61.86890708333218 msec\nrounds: 12"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-gpmc-False]",
            "value": 25.73787967454348,
            "unit": "iter/sec",
            "range": "stddev: 0.0004123521405010684",
            "extra": "mean: 38.85323937500059 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-difference-ganak-False]",
            "value": 25.187821882260348,
            "unit": "iter/sec",
            "range": "stddev: 0.003322911128227443",
            "extra": "mean: 39.701725884614696 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-gpmc-False]",
            "value": 27.739122265179688,
            "unit": "iter/sec",
            "range": "stddev: 0.00048249833090645755",
            "extra": "mean: 36.05016735714374 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-proportional-ganak-False]",
            "value": 27.43197785768308,
            "unit": "iter/sec",
            "range": "stddev: 0.0014275834949897754",
            "extra": "mean: 36.45380603571472 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-gpmc-False]",
            "value": 27.62684620506962,
            "unit": "iter/sec",
            "range": "stddev: 0.0006631745984911986",
            "extra": "mean: 36.19667596428349 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-naive-ganak-False]",
            "value": 27.52951537909479,
            "unit": "iter/sec",
            "range": "stddev: 0.0005588099829915025",
            "extra": "mean: 36.32464960714036 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-False]",
            "value": 18.892717155854537,
            "unit": "iter/sec",
            "range": "stddev: 0.0047436444306415",
            "extra": "mean: 52.930448899994076 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-False]",
            "value": 18.859200902465325,
            "unit": "iter/sec",
            "range": "stddev: 0.011337156904170817",
            "extra": "mean: 53.02451600000069 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 6.220805132950395,
            "unit": "iter/sec",
            "range": "stddev: 0.0015612887988232147",
            "extra": "mean: 160.75089616667051 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 6.134681446758377,
            "unit": "iter/sec",
            "range": "stddev: 0.0010551796130170094",
            "extra": "mean: 163.00764899999973 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 6.7302643638707815,
            "unit": "iter/sec",
            "range": "stddev: 0.00194185099854807",
            "extra": "mean: 148.58257357142944 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 6.458072308813894,
            "unit": "iter/sec",
            "range": "stddev: 0.02210467359988324",
            "extra": "mean: 154.84496800000412 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 6.761094743015411,
            "unit": "iter/sec",
            "range": "stddev: 0.0016814010311759278",
            "extra": "mean: 147.90504171429575 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 6.73004765964973,
            "unit": "iter/sec",
            "range": "stddev: 0.001983593323428485",
            "extra": "mean: 148.58735785714268 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 6.454629163927054,
            "unit": "iter/sec",
            "range": "stddev: 0.0010987523156892338",
            "extra": "mean: 154.92756819999727 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 6.3883138917120945,
            "unit": "iter/sec",
            "range": "stddev: 0.0010178234990543076",
            "extra": "mean: 156.5358272857184 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.5826011982535055,
            "unit": "iter/sec",
            "range": "stddev: 0.029370605734665132",
            "extra": "mean: 218.21667580000508 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.5221958171751029,
            "unit": "iter/sec",
            "range": "stddev: 0.002729685934114511",
            "extra": "mean: 656.9457021999995 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 4.8877341189085435,
            "unit": "iter/sec",
            "range": "stddev: 0.002674070727071139",
            "extra": "mean: 204.5937801999969 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.146325586078321,
            "unit": "iter/sec",
            "range": "stddev: 0.0443732363698952",
            "extra": "mean: 872.3525080000059 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 4.85709931976992,
            "unit": "iter/sec",
            "range": "stddev: 0.0018155701083385786",
            "extra": "mean: 205.88419839999688 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.1660502422518488,
            "unit": "iter/sec",
            "range": "stddev: 0.029797540003059113",
            "extra": "mean: 857.5959797999985 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 3.3847172471080866,
            "unit": "iter/sec",
            "range": "stddev: 0.019322461579669617",
            "extra": "mean: 295.4456538000045 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1375984969466122,
            "unit": "iter/sec",
            "range": "stddev: 0.028827778518830977",
            "extra": "mean: 879.0447620000066 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-gpmc-False]",
            "value": 1.2174923817934507,
            "unit": "iter/sec",
            "range": "stddev: 0.03615934429964008",
            "extra": "mean: 821.3603755999941 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-difference-ganak-False]",
            "value": 0.5076446199768812,
            "unit": "iter/sec",
            "range": "stddev: 0.005175669435033291",
            "extra": "mean: 1.9698820013999978 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.3917941586766636,
            "unit": "iter/sec",
            "range": "stddev: 0.0049425058722061795",
            "extra": "mean: 718.4970519999979 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5290145102215602,
            "unit": "iter/sec",
            "range": "stddev: 0.029856777946315322",
            "extra": "mean: 1.8903073179999978 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-gpmc-False]",
            "value": 1.3148933244021308,
            "unit": "iter/sec",
            "range": "stddev: 0.0388932260829525",
            "extra": "mean: 760.5179685999929 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-naive-ganak-False]",
            "value": 0.5195260770865614,
            "unit": "iter/sec",
            "range": "stddev: 0.03437811109648683",
            "extra": "mean: 1.924831195400003 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-gpmc-False]",
            "value": 1.1765432689881081,
            "unit": "iter/sec",
            "range": "stddev: 0.03290572129250419",
            "extra": "mean: 849.9474914000018 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-straightforward-ganak-False]",
            "value": 0.5036602937676836,
            "unit": "iter/sec",
            "range": "stddev: 0.0068529698880587",
            "extra": "mean: 1.9854652279999983 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-gpmc-False]",
            "value": 0.44161012471690053,
            "unit": "iter/sec",
            "range": "stddev: 0.039283101402164886",
            "extra": "mean: 2.264440835999994 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-difference-ganak-False]",
            "value": 0.44189360102383773,
            "unit": "iter/sec",
            "range": "stddev: 0.03215084799697476",
            "extra": "mean: 2.2629881891999957 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-False]",
            "value": 0.48792641685382243,
            "unit": "iter/sec",
            "range": "stddev: 0.08707956430428511",
            "extra": "mean: 2.049489360399991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-False]",
            "value": 0.48459133265743704,
            "unit": "iter/sec",
            "range": "stddev: 0.056081023755309",
            "extra": "mean: 2.06359448180001 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 0.4811768646544212,
            "unit": "iter/sec",
            "range": "stddev: 0.03169150307780672",
            "extra": "mean: 2.0782379068000183 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 0.47659423897728154,
            "unit": "iter/sec",
            "range": "stddev: 0.043612354173748424",
            "extra": "mean: 2.0982209145999944 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-gpmc-False]",
            "value": 0.5105209692914479,
            "unit": "iter/sec",
            "range": "stddev: 0.037737296518756167",
            "extra": "mean: 1.9587834000000044 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-straightforward-ganak-False]",
            "value": 0.5073831080219343,
            "unit": "iter/sec",
            "range": "stddev: 0.0348370598774263",
            "extra": "mean: 1.9708973045999982 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-gpmc-False]",
            "value": 4.530720941627047,
            "unit": "iter/sec",
            "range": "stddev: 0.0016910627968868995",
            "extra": "mean: 220.71542540002156 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-difference-ganak-False]",
            "value": 1.0291963336017536,
            "unit": "iter/sec",
            "range": "stddev: 0.03335527342982755",
            "extra": "mean: 971.6319106000128 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.182371482709251,
            "unit": "iter/sec",
            "range": "stddev: 0.001275104107805444",
            "extra": "mean: 161.750228499983 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0832085152522077,
            "unit": "iter/sec",
            "range": "stddev: 0.0024581696548860135",
            "extra": "mean: 923.183289200017 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-gpmc-False]",
            "value": 5.686324540168589,
            "unit": "iter/sec",
            "range": "stddev: 0.027693769122365017",
            "extra": "mean: 175.86052166666377 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-naive-ganak-False]",
            "value": 1.0906823126731375,
            "unit": "iter/sec",
            "range": "stddev: 0.0026155318637383447",
            "extra": "mean: 916.8572629999971 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-gpmc-False]",
            "value": 5.1907992514356724,
            "unit": "iter/sec",
            "range": "stddev: 0.0017330620951890392",
            "extra": "mean: 192.64855979999993 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-straightforward-ganak-False]",
            "value": 1.1033520443274105,
            "unit": "iter/sec",
            "range": "stddev: 0.02998851350985918",
            "extra": "mean: 906.3290408000171 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "d4e05ef026a1f8f28e2dd9a1687a0aa3af212116",
          "message": "fix: 🐛 Refactor timeout handling in generate_test functions for improved resource management",
          "timestamp": "2026-01-15T14:04:27+08:00",
          "tree_id": "85afbb21b61bf459367654561b9ac9e727da584a",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/d4e05ef026a1f8f28e2dd9a1687a0aa3af212116"
        },
        "date": 1768457234125,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.49430108944596673,
            "unit": "iter/sec",
            "range": "stddev: 0.01564110174619115",
            "extra": "mean: 2.023058458400004 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.871737252770759,
            "unit": "iter/sec",
            "range": "stddev: 0.01514403292116903",
            "extra": "mean: 101.29929255555543 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 97.03040270311656,
            "unit": "iter/sec",
            "range": "stddev: 0.0011596455653362825",
            "extra": "mean: 10.3060481265825 msec\nrounds: 79"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.831071167239273,
            "unit": "iter/sec",
            "range": "stddev: 0.0002957518603000862",
            "extra": "mean: 59.41392499999901 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 21.573647006135037,
            "unit": "iter/sec",
            "range": "stddev: 0.000400777480091481",
            "extra": "mean: 46.35284890475975 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 21.54604307873817,
            "unit": "iter/sec",
            "range": "stddev: 0.00038432073649085057",
            "extra": "mean: 46.412234318180175 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 6.929172232631739,
            "unit": "iter/sec",
            "range": "stddev: 0.014294213144536402",
            "extra": "mean: 144.3173825714236 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.043689658763147,
            "unit": "iter/sec",
            "range": "stddev: 0.009164927394730371",
            "extra": "mean: 141.97104762500246 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.906679196153101,
            "unit": "iter/sec",
            "range": "stddev: 0.0007617881964619354",
            "extra": "mean: 203.8038274000087 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.019021189537409,
            "unit": "iter/sec",
            "range": "stddev: 0.004768623437373524",
            "extra": "mean: 981.3338626000075 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4732803257679818,
            "unit": "iter/sec",
            "range": "stddev: 0.016255800642056274",
            "extra": "mean: 678.7574519999964 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.544085216611447,
            "unit": "iter/sec",
            "range": "stddev: 0.017848159604415752",
            "extra": "mean: 1.8379473830000053 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46843335746564063,
            "unit": "iter/sec",
            "range": "stddev: 0.025260308442676644",
            "extra": "mean: 2.134775382799995 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.45563922101046156,
            "unit": "iter/sec",
            "range": "stddev: 0.004122301616687213",
            "extra": "mean: 2.1947188781999953 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.147342069222086,
            "unit": "iter/sec",
            "range": "stddev: 0.01898870091876236",
            "extra": "mean: 162.67193019999695 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.09521418551291,
            "unit": "iter/sec",
            "range": "stddev: 0.0025622899334832813",
            "extra": "mean: 913.063410999996 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "07d19453ca61d27e38289ba3fe2030415b3fe333",
          "message": "feat: Configure setuptools-scm for dynamic versioning and add a script to install Linux build dependencies.",
          "timestamp": "2026-01-15T23:40:21+08:00",
          "tree_id": "088e1c3475bf648800b7a1fe2a509e5d4e1eca21",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/07d19453ca61d27e38289ba3fe2030415b3fe333"
        },
        "date": 1768491818749,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.4886266287657955,
            "unit": "iter/sec",
            "range": "stddev: 0.00755788152595784",
            "extra": "mean: 2.046552400400003 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.453583205823634,
            "unit": "iter/sec",
            "range": "stddev: 0.01813443780853346",
            "extra": "mean: 105.77999666665822 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 97.72089718213677,
            "unit": "iter/sec",
            "range": "stddev: 0.00016205177991883874",
            "extra": "mean: 10.233225736109988 msec\nrounds: 72"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 15.852283235022966,
            "unit": "iter/sec",
            "range": "stddev: 0.0005988082311159313",
            "extra": "mean: 63.08239546153625 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 20.930240170906742,
            "unit": "iter/sec",
            "range": "stddev: 0.0004711286344689709",
            "extra": "mean: 47.777760399998215 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 20.955286951746178,
            "unit": "iter/sec",
            "range": "stddev: 0.0004535168377711392",
            "extra": "mean: 47.72065409090813 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 6.524544575184223,
            "unit": "iter/sec",
            "range": "stddev: 0.018039156893049704",
            "extra": "mean: 153.26740257143 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 6.988580686239452,
            "unit": "iter/sec",
            "range": "stddev: 0.0005795607596711968",
            "extra": "mean: 143.09057087499966 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.633411183877302,
            "unit": "iter/sec",
            "range": "stddev: 0.0052512305562909525",
            "extra": "mean: 215.82371179999313 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.0136794205064985,
            "unit": "iter/sec",
            "range": "stddev: 0.0057739776853466575",
            "extra": "mean: 986.5051807999976 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4549436058417278,
            "unit": "iter/sec",
            "range": "stddev: 0.025668909537730995",
            "extra": "mean: 687.3118627999816 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5429559933880681,
            "unit": "iter/sec",
            "range": "stddev: 0.01924116358412908",
            "extra": "mean: 1.841769889599999 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46154599896806014,
            "unit": "iter/sec",
            "range": "stddev: 0.02888872575411303",
            "extra": "mean: 2.166631283200013 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.45353835419980565,
            "unit": "iter/sec",
            "range": "stddev: 0.0250076343266248",
            "extra": "mean: 2.204885189399994 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.028550452936178,
            "unit": "iter/sec",
            "range": "stddev: 0.022406786900908103",
            "extra": "mean: 165.87735440000415 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0930121605356897,
            "unit": "iter/sec",
            "range": "stddev: 0.002768967326507475",
            "extra": "mean: 914.9029041999825 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "5634a5541f6ba1c5fb5b3fe274d5d94058918131",
          "message": "build: Enforce C++11 standard and verbose output in the build script.",
          "timestamp": "2026-01-16T00:00:12+08:00",
          "tree_id": "95f3d06cdc71a6d35106f2e0cb5099573029ad14",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/5634a5541f6ba1c5fb5b3fe274d5d94058918131"
        },
        "date": 1768493004671,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.4930741025639469,
            "unit": "iter/sec",
            "range": "stddev: 0.02818549691629097",
            "extra": "mean: 2.0280927243999995 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.697954199320545,
            "unit": "iter/sec",
            "range": "stddev: 0.014494245752004246",
            "extra": "mean: 103.11453111111429 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 99.36714322370514,
            "unit": "iter/sec",
            "range": "stddev: 0.00019118890275293194",
            "extra": "mean: 10.063688736111706 msec\nrounds: 72"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 15.840599758640838,
            "unit": "iter/sec",
            "range": "stddev: 0.00395249671693641",
            "extra": "mean: 63.128922846151276 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 21.135337581053818,
            "unit": "iter/sec",
            "range": "stddev: 0.0007446483410759152",
            "extra": "mean: 47.31412479999477 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 21.083661988090114,
            "unit": "iter/sec",
            "range": "stddev: 0.0005143143366058415",
            "extra": "mean: 47.430090681822115 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 6.773785255202921,
            "unit": "iter/sec",
            "range": "stddev: 0.017891396846810237",
            "extra": "mean: 147.62794542857753 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.039993330029034,
            "unit": "iter/sec",
            "range": "stddev: 0.0018763724691203795",
            "extra": "mean: 142.04558912499365 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.725763075556281,
            "unit": "iter/sec",
            "range": "stddev: 0.001137724702438524",
            "extra": "mean: 211.6060377999986 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.0150527206669349,
            "unit": "iter/sec",
            "range": "stddev: 0.005973793975843931",
            "extra": "mean: 985.1705036000055 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4032737620785278,
            "unit": "iter/sec",
            "range": "stddev: 0.04385761767275317",
            "extra": "mean: 712.6193242000056 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5352765664372718,
            "unit": "iter/sec",
            "range": "stddev: 0.02865285338967297",
            "extra": "mean: 1.868193122400004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.4528471896085621,
            "unit": "iter/sec",
            "range": "stddev: 0.03600073388832724",
            "extra": "mean: 2.2082504274000088 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.44547991248847957,
            "unit": "iter/sec",
            "range": "stddev: 0.03132086061957884",
            "extra": "mean: 2.2447701275999976 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 5.8795919332251065,
            "unit": "iter/sec",
            "range": "stddev: 0.02494861134520716",
            "extra": "mean: 170.07983059999106 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0890663925530217,
            "unit": "iter/sec",
            "range": "stddev: 0.002807680321721717",
            "extra": "mean: 918.2176649999917 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "0472d9030dd7e3f7884b118913bb998e052dab7e",
          "message": "build: Integrate setuptools-scm for dynamic versioning and remove the `cp314*` skip from CI builds.",
          "timestamp": "2026-01-16T00:27:20+08:00",
          "tree_id": "0f4268d46f5056010a616a734013c49b249c5c20",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/0472d9030dd7e3f7884b118913bb998e052dab7e"
        },
        "date": 1768494639885,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.5009685436262646,
            "unit": "iter/sec",
            "range": "stddev: 0.02127501370513469",
            "extra": "mean: 1.9961333156000023 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.601325566688594,
            "unit": "iter/sec",
            "range": "stddev: 0.013238174693671436",
            "extra": "mean: 104.15228533333556 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 102.2043656035159,
            "unit": "iter/sec",
            "range": "stddev: 0.00009967885373993415",
            "extra": "mean: 9.78431786250038 msec\nrounds: 80"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.90533305948952,
            "unit": "iter/sec",
            "range": "stddev: 0.00023770132230300532",
            "extra": "mean: 59.15293099999985 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-gpmc-True]",
            "value": 21.550649900844444,
            "unit": "iter/sec",
            "range": "stddev: 0.00034668935170598694",
            "extra": "mean: 46.40231290476377 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-ganak-True]",
            "value": 21.60145704891288,
            "unit": "iter/sec",
            "range": "stddev: 0.0004166420805582372",
            "extra": "mean: 46.29317354545425 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-gpmc-False]",
            "value": 6.9118247935987025,
            "unit": "iter/sec",
            "range": "stddev: 0.017003834513909875",
            "extra": "mean: 144.6795932857177 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-ganak-False]",
            "value": 7.229975283348232,
            "unit": "iter/sec",
            "range": "stddev: 0.000665267315128864",
            "extra": "mean: 138.31305928571527 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-True]",
            "value": 4.930892189962368,
            "unit": "iter/sec",
            "range": "stddev: 0.0006665317456984501",
            "extra": "mean: 202.80305499999827 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-True]",
            "value": 1.0241609313722795,
            "unit": "iter/sec",
            "range": "stddev: 0.0036613626472408204",
            "extra": "mean: 976.4090479999993 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-gpmc-False]",
            "value": 1.4765234548414503,
            "unit": "iter/sec",
            "range": "stddev: 0.01901188159746109",
            "extra": "mean: 677.2665863999975 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-ganak-False]",
            "value": 0.5472273235908583,
            "unit": "iter/sec",
            "range": "stddev: 0.019064581620223314",
            "extra": "mean: 1.8273941320000007 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-gpmc-True]",
            "value": 0.46960391194838114,
            "unit": "iter/sec",
            "range": "stddev: 0.01088821302585785",
            "extra": "mean: 2.129454151799996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-ganak-True]",
            "value": 0.460226459206405,
            "unit": "iter/sec",
            "range": "stddev: 0.025174201564830044",
            "extra": "mean: 2.1728433469999913 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-gpmc-False]",
            "value": 6.271481132048968,
            "unit": "iter/sec",
            "range": "stddev: 0.018092104158643173",
            "extra": "mean: 159.45196659999965 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-ganak-False]",
            "value": 1.0993056010813134,
            "unit": "iter/sec",
            "range": "stddev: 0.0009640436576827579",
            "extra": "mean: 909.665154999999 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "9f2693b36bc7f9b1aafba94679f9c79640ad8336",
          "message": "refactor: ✨ Simplify test parameterization and enhance readability and change pytest.yml will not git at push tag",
          "timestamp": "2026-01-16T08:32:58+08:00",
          "tree_id": "84155bec03fc41db090e87d80244ae55dbbc11a8",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/9f2693b36bc7f9b1aafba94679f9c79640ad8336"
        },
        "date": 1768523750562,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False]",
            "value": 0.4956096253819472,
            "unit": "iter/sec",
            "range": "stddev: 0.02413417524435603",
            "extra": "mean: 2.017717067600006 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False]",
            "value": 9.820045291402165,
            "unit": "iter/sec",
            "range": "stddev: 0.013646512864425411",
            "extra": "mean: 101.83252422221913 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True]",
            "value": 100.88658620799987,
            "unit": "iter/sec",
            "range": "stddev: 0.00016317396989726866",
            "extra": "mean: 9.91212050666756 msec\nrounds: 75"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True]",
            "value": 16.420320554921343,
            "unit": "iter/sec",
            "range": "stddev: 0.0004414450292901761",
            "extra": "mean: 60.9001509230762 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc]",
            "value": 21.12147031928133,
            "unit": "iter/sec",
            "range": "stddev: 0.0004512142365837829",
            "extra": "mean: 47.34518880000138 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak]",
            "value": 21.208007816761118,
            "unit": "iter/sec",
            "range": "stddev: 0.00035854603899268295",
            "extra": "mean: 47.15200072727622 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc]",
            "value": 6.594028388545174,
            "unit": "iter/sec",
            "range": "stddev: 0.017127431413411803",
            "extra": "mean: 151.65236499999781 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak]",
            "value": 7.077181254672751,
            "unit": "iter/sec",
            "range": "stddev: 0.0006427551876528278",
            "extra": "mean: 141.29919300000182 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc]",
            "value": 4.819014679989819,
            "unit": "iter/sec",
            "range": "stddev: 0.001743570783285135",
            "extra": "mean: 207.51129980000655 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak]",
            "value": 1.018973772186133,
            "unit": "iter/sec",
            "range": "stddev: 0.006343244508908421",
            "extra": "mean: 981.3795284000037 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc]",
            "value": 1.428952115296201,
            "unit": "iter/sec",
            "range": "stddev: 0.02732720163572195",
            "extra": "mean: 699.8135131999959 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak]",
            "value": 0.5433239901644817,
            "unit": "iter/sec",
            "range": "stddev: 0.014498428890053134",
            "extra": "mean: 1.8405224471999986 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc]",
            "value": 0.4640462767186979,
            "unit": "iter/sec",
            "range": "stddev: 0.022239736890207275",
            "extra": "mean: 2.1549574906000033 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak]",
            "value": 0.45768060903197755,
            "unit": "iter/sec",
            "range": "stddev: 0.02701401221494304",
            "extra": "mean: 2.184929796599994 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc]",
            "value": 6.103249710463429,
            "unit": "iter/sec",
            "range": "stddev: 0.020414879512164263",
            "extra": "mean: 163.84713839998994 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak]",
            "value": 1.095085341658622,
            "unit": "iter/sec",
            "range": "stddev: 0.0006181464408490815",
            "extra": "mean: 913.1708388000106 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "ce3fe41aa09168341c1c7f4a88a18ba8251b7052",
          "message": "Rust Backend Integration & Maturin Migration (#20)\n\nRust Backend Integration & Maturin Migration",
          "timestamp": "2026-03-19T00:45:34+08:00",
          "tree_id": "2ad600fab4928e9df31df482042cc6e2b9aee843",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/ce3fe41aa09168341c1c7f4a88a18ba8251b7052"
        },
        "date": 1773852877045,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.5569583504009179,
            "unit": "iter/sec",
            "range": "stddev: 0.017279493520952188",
            "extra": "mean: 1.795466392200001 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 188.66654594606067,
            "unit": "iter/sec",
            "range": "stddev: 0.00010405971866945153",
            "extra": "mean: 5.300356748386637 msec\nrounds: 155"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 11.037141452239775,
            "unit": "iter/sec",
            "range": "stddev: 0.017257398595433848",
            "extra": "mean: 90.60316969998325 msec\nrounds: 10"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1726.1932172080565,
            "unit": "iter/sec",
            "range": "stddev: 0.000021417211015448626",
            "extra": "mean: 579.3094249422433 usec\nrounds: 1299"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 111.3450302067704,
            "unit": "iter/sec",
            "range": "stddev: 0.0007981269588032226",
            "extra": "mean: 8.981092358976202 msec\nrounds: 78"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 6801.379236954747,
            "unit": "iter/sec",
            "range": "stddev: 0.00003574211286736594",
            "extra": "mean: 147.02900178931066 usec\nrounds: 3353"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 18.190147757583848,
            "unit": "iter/sec",
            "range": "stddev: 0.0003389672416277186",
            "extra": "mean: 54.97481457142531 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1909.7076284363127,
            "unit": "iter/sec",
            "range": "stddev: 0.000026064806900803525",
            "extra": "mean: 523.6403652106736 usec\nrounds: 1328"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 24.589850330584596,
            "unit": "iter/sec",
            "range": "stddev: 0.0002895936130591374",
            "extra": "mean: 40.66718530434529 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 4692.974362863708,
            "unit": "iter/sec",
            "range": "stddev: 0.000048626014903520636",
            "extra": "mean: 213.08447962408817 usec\nrounds: 2552"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 24.67452924028143,
            "unit": "iter/sec",
            "range": "stddev: 0.0003579521387835087",
            "extra": "mean: 40.52762224000162 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 4708.592503377363,
            "unit": "iter/sec",
            "range": "stddev: 0.000006542318818697333",
            "extra": "mean: 212.37769020842714 usec\nrounds: 2747"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 7.635522560646653,
            "unit": "iter/sec",
            "range": "stddev: 0.019184510946933395",
            "extra": "mean: 130.9668057500062 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 740.8968504913845,
            "unit": "iter/sec",
            "range": "stddev: 0.000016128045654476773",
            "extra": "mean: 1.349715549926782 msec\nrounds: 671"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 8.053499526207762,
            "unit": "iter/sec",
            "range": "stddev: 0.0007312672647676545",
            "extra": "mean: 124.16962300001286 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 736.9434349851131,
            "unit": "iter/sec",
            "range": "stddev: 0.000012991110362846748",
            "extra": "mean: 1.3569562500006542 msec\nrounds: 664"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.968471308289979,
            "unit": "iter/sec",
            "range": "stddev: 0.002087580423233018",
            "extra": "mean: 201.269150600001 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 59.43473357274207,
            "unit": "iter/sec",
            "range": "stddev: 0.00038390471964155833",
            "extra": "mean: 16.825178475412898 msec\nrounds: 61"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 0.9509294032047894,
            "unit": "iter/sec",
            "range": "stddev: 0.0016819501292839043",
            "extra": "mean: 1.0516027758000064 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.2002296812328088,
            "unit": "iter/sec",
            "range": "stddev: 0.0039665768735009715",
            "extra": "mean: 833.1738630000018 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4810736196979442,
            "unit": "iter/sec",
            "range": "stddev: 0.025707043718863398",
            "extra": "mean: 675.1858832000153 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 20.535148894220722,
            "unit": "iter/sec",
            "range": "stddev: 0.0009323557866314365",
            "extra": "mean: 48.69699290475724 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5034940799928889,
            "unit": "iter/sec",
            "range": "stddev: 0.03474188408969111",
            "extra": "mean: 1.986120670999992 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.7392939985718782,
            "unit": "iter/sec",
            "range": "stddev: 0.0006464938487598776",
            "extra": "mean: 1.3526418474000024 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4929103704263885,
            "unit": "iter/sec",
            "range": "stddev: 0.027959979736179037",
            "extra": "mean: 2.0287664046000033 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1636505569572424,
            "unit": "iter/sec",
            "range": "stddev: 0.006003624026452527",
            "extra": "mean: 859.3645180000067 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.4322436508730626,
            "unit": "iter/sec",
            "range": "stddev: 0.009763625131471472",
            "extra": "mean: 2.31350997979996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9328315669399196,
            "unit": "iter/sec",
            "range": "stddev: 0.0013530235070947029",
            "extra": "mean: 1.0720048886000086 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.166100012147003,
            "unit": "iter/sec",
            "range": "stddev: 0.026906051397262435",
            "extra": "mean: 162.1770645999959 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 70.59225202249795,
            "unit": "iter/sec",
            "range": "stddev: 0.0002669597370436358",
            "extra": "mean: 14.165860577465319 msec\nrounds: 71"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0112724399023352,
            "unit": "iter/sec",
            "range": "stddev: 0.0037862076381037003",
            "extra": "mean: 988.8532116000079 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.018055708288352,
            "unit": "iter/sec",
            "range": "stddev: 0.0011257529289846998",
            "extra": "mean: 495.5264593999573 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "2057f51c4bbf282a41f19565dd7f3502038e31bf",
          "message": "fix(build): sync versioning, remove pyo3 from pathsum, and fix macOS GMP/MPFR include paths for cmake",
          "timestamp": "2026-03-19T01:20:53+08:00",
          "tree_id": "abf9da13bdc0bd2772a5b3c07f2097b2b9b4b47f",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/2057f51c4bbf282a41f19565dd7f3502038e31bf"
        },
        "date": 1773854695829,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.48601098017915756,
            "unit": "iter/sec",
            "range": "stddev: 0.011977472971174784",
            "extra": "mean: 2.057566682200002 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 191.57574717605726,
            "unit": "iter/sec",
            "range": "stddev: 0.000059651272939834154",
            "extra": "mean: 5.21986741401564 msec\nrounds: 157"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.703359952152345,
            "unit": "iter/sec",
            "range": "stddev: 0.013564839748567838",
            "extra": "mean: 103.0570858889127 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1596.653056122112,
            "unit": "iter/sec",
            "range": "stddev: 0.000012612136858796145",
            "extra": "mean: 626.310140556622 usec\nrounds: 1366"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 99.84902145654806,
            "unit": "iter/sec",
            "range": "stddev: 0.00015221757740558093",
            "extra": "mean: 10.01512068333265 msec\nrounds: 60"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5453.4745959896245,
            "unit": "iter/sec",
            "range": "stddev: 0.000010821049738621037",
            "extra": "mean: 183.36933314686746 usec\nrounds: 3572"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.36859759628678,
            "unit": "iter/sec",
            "range": "stddev: 0.0011409965607480806",
            "extra": "mean: 61.09258866665831 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1724.8689849336588,
            "unit": "iter/sec",
            "range": "stddev: 0.00005994269384670409",
            "extra": "mean: 579.7541776997408 usec\nrounds: 1435"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.70467707961342,
            "unit": "iter/sec",
            "range": "stddev: 0.003487714274304723",
            "extra": "mean: 48.298265949998154 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3865.4040845866634,
            "unit": "iter/sec",
            "range": "stddev: 0.000010399894123595131",
            "extra": "mean: 258.705164613322 usec\nrounds: 2515"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 21.224570381559175,
            "unit": "iter/sec",
            "range": "stddev: 0.0005660740017893593",
            "extra": "mean: 47.11520572726613 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3856.161142607873,
            "unit": "iter/sec",
            "range": "stddev: 0.000009754003301378815",
            "extra": "mean: 259.325262357608 usec\nrounds: 2893"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.87536759214219,
            "unit": "iter/sec",
            "range": "stddev: 0.01617334682992874",
            "extra": "mean: 145.4467687142856 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 744.2435543823514,
            "unit": "iter/sec",
            "range": "stddev: 0.00005139174571022433",
            "extra": "mean: 1.3436461681282565 msec\nrounds: 684"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 7.1765120110626714,
            "unit": "iter/sec",
            "range": "stddev: 0.0005357354539317384",
            "extra": "mean: 139.34345799999903 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 739.0057137055181,
            "unit": "iter/sec",
            "range": "stddev: 0.00003290323309350386",
            "extra": "mean: 1.3531695106737482 msec\nrounds: 609"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.908777035104027,
            "unit": "iter/sec",
            "range": "stddev: 0.0007588354721075095",
            "extra": "mean: 203.71672880000915 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 66.10124754527017,
            "unit": "iter/sec",
            "range": "stddev: 0.0006987666367722119",
            "extra": "mean: 15.128307515151494 msec\nrounds: 66"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 1.0239378131536672,
            "unit": "iter/sec",
            "range": "stddev: 0.002039815365574634",
            "extra": "mean: 976.6218095999989 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.3166281311556538,
            "unit": "iter/sec",
            "range": "stddev: 0.0021554668554486854",
            "extra": "mean: 759.5158999999967 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4942628944681065,
            "unit": "iter/sec",
            "range": "stddev: 0.01795091356500908",
            "extra": "mean: 669.226281199974 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 20.936719331113398,
            "unit": "iter/sec",
            "range": "stddev: 0.00029654695796372",
            "extra": "mean: 47.7629749047613 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5441814866711862,
            "unit": "iter/sec",
            "range": "stddev: 0.026438113124719158",
            "extra": "mean: 1.8376222353999991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.8177014561608458,
            "unit": "iter/sec",
            "range": "stddev: 0.0019200561764245523",
            "extra": "mean: 1.2229402216000154 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5096632355881128,
            "unit": "iter/sec",
            "range": "stddev: 0.0211676019988883",
            "extra": "mean: 1.9620799189999958 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1911002297233715,
            "unit": "iter/sec",
            "range": "stddev: 0.004770762870261597",
            "extra": "mean: 839.5599086000061 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.45631804384856717,
            "unit": "iter/sec",
            "range": "stddev: 0.02486713200977565",
            "extra": "mean: 2.191453994599999 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9915180682041085,
            "unit": "iter/sec",
            "range": "stddev: 0.0026574366942492544",
            "extra": "mean: 1.008554490400013 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.324913628971801,
            "unit": "iter/sec",
            "range": "stddev: 0.0205840037302264",
            "extra": "mean: 158.10492580000073 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 80.85112284045296,
            "unit": "iter/sec",
            "range": "stddev: 0.0003250495855258619",
            "extra": "mean: 12.368412025314028 msec\nrounds: 79"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.097184412579902,
            "unit": "iter/sec",
            "range": "stddev: 0.0007188839957773648",
            "extra": "mean: 911.4238122000074 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.226110617127494,
            "unit": "iter/sec",
            "range": "stddev: 0.0016968783423673233",
            "extra": "mean: 449.213975400005 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "9ebe0a25a26f8cac72845182eb2e17f504b7b9b3",
          "message": "chore: release v0.13.0",
          "timestamp": "2026-03-19T01:38:46+08:00",
          "tree_id": "ad3aefdb03ec964b527f00404e0d34da420203fb",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/9ebe0a25a26f8cac72845182eb2e17f504b7b9b3"
        },
        "date": 1773855820447,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.5386756362865535,
            "unit": "iter/sec",
            "range": "stddev: 0.02359151531850299",
            "extra": "mean: 1.8564047316000027 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 181.23054612012442,
            "unit": "iter/sec",
            "range": "stddev: 0.00007313249374245407",
            "extra": "mean: 5.517833618054506 msec\nrounds: 144"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 10.704540232043058,
            "unit": "iter/sec",
            "range": "stddev: 0.019261302872065213",
            "extra": "mean: 93.41830460000438 msec\nrounds: 10"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1608.2648682255792,
            "unit": "iter/sec",
            "range": "stddev: 0.000026338236351728907",
            "extra": "mean: 621.788126916752 usec\nrounds: 1174"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 113.90330833583943,
            "unit": "iter/sec",
            "range": "stddev: 0.00018434429058572982",
            "extra": "mean: 8.77937624999916 msec\nrounds: 80"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 6344.897101735486,
            "unit": "iter/sec",
            "range": "stddev: 0.000009680534928505107",
            "extra": "mean: 157.60696887053933 usec\nrounds: 3116"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 17.963332662842408,
            "unit": "iter/sec",
            "range": "stddev: 0.000698425248661153",
            "extra": "mean: 55.66895735714589 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1786.6156558019647,
            "unit": "iter/sec",
            "range": "stddev: 0.00001825182679438261",
            "extra": "mean: 559.7174729509053 usec\nrounds: 1220"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 23.23808054679805,
            "unit": "iter/sec",
            "range": "stddev: 0.00043606196040054914",
            "extra": "mean: 43.03281409091204 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 4273.184905050385,
            "unit": "iter/sec",
            "range": "stddev: 0.00006552351638593941",
            "extra": "mean: 234.0174886460264 usec\nrounds: 2378"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 23.28699277724001,
            "unit": "iter/sec",
            "range": "stddev: 0.0004681223932596939",
            "extra": "mean: 42.94242754166907 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 4325.56175054676,
            "unit": "iter/sec",
            "range": "stddev: 0.000012087177339068111",
            "extra": "mean: 231.1838456296683 usec\nrounds: 2494"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 7.544355574523798,
            "unit": "iter/sec",
            "range": "stddev: 0.023100893545441783",
            "extra": "mean: 132.54942587500196 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 717.7513606689981,
            "unit": "iter/sec",
            "range": "stddev: 0.00002495430523691692",
            "extra": "mean: 1.3932401313289395 msec\nrounds: 632"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 8.008178448338464,
            "unit": "iter/sec",
            "range": "stddev: 0.0006982993561325159",
            "extra": "mean: 124.87234225000066 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 720.7921294189628,
            "unit": "iter/sec",
            "range": "stddev: 0.000026190584765515376",
            "extra": "mean: 1.3873625407176815 msec\nrounds: 614"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.734994583644408,
            "unit": "iter/sec",
            "range": "stddev: 0.03469954300235532",
            "extra": "mean: 211.193483400001 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 57.22370528769797,
            "unit": "iter/sec",
            "range": "stddev: 0.0002549476819215671",
            "extra": "mean: 17.47527523728844 msec\nrounds: 59"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 0.962836697585478,
            "unit": "iter/sec",
            "range": "stddev: 0.006190429995631534",
            "extra": "mean: 1.0385977211999886 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.2132632001525736,
            "unit": "iter/sec",
            "range": "stddev: 0.0010838286320510543",
            "extra": "mean: 824.2234659999951 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4761504409238917,
            "unit": "iter/sec",
            "range": "stddev: 0.04056616107202144",
            "extra": "mean: 677.4377274000074 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.176396476202065,
            "unit": "iter/sec",
            "range": "stddev: 0.0004499974061422135",
            "extra": "mean: 52.14744079999605 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5197983983701849,
            "unit": "iter/sec",
            "range": "stddev: 0.030310643167904095",
            "extra": "mean: 1.9238227804000076 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.7595996582686917,
            "unit": "iter/sec",
            "range": "stddev: 0.0006619031879502713",
            "extra": "mean: 1.3164829514000018 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5049396450413938,
            "unit": "iter/sec",
            "range": "stddev: 0.03706113594063779",
            "extra": "mean: 1.9804347110000093 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1034218502328714,
            "unit": "iter/sec",
            "range": "stddev: 0.002430715372462411",
            "extra": "mean: 906.2717035999924 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.4434432479364611,
            "unit": "iter/sec",
            "range": "stddev: 0.015225324081218189",
            "extra": "mean: 2.2550800010000045 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9139952671051006,
            "unit": "iter/sec",
            "range": "stddev: 0.0011449718329821113",
            "extra": "mean: 1.0940975692000052 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.430679084560344,
            "unit": "iter/sec",
            "range": "stddev: 0.03538054396047976",
            "extra": "mean: 155.50457219999316 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 73.04481943787248,
            "unit": "iter/sec",
            "range": "stddev: 0.00030874277443418695",
            "extra": "mean: 13.69022481944171 msec\nrounds: 72"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0385365659220163,
            "unit": "iter/sec",
            "range": "stddev: 0.001143577779676622",
            "extra": "mean: 962.8933952000011 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.082133251588398,
            "unit": "iter/sec",
            "range": "stddev: 0.0027187354849103483",
            "extra": "mean: 480.27665820001175 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "fac91df5f3d24cdad121065f2b782f025317268c",
          "message": "fix(build): bypass pkg-config check for GMP/MPFR on Linux",
          "timestamp": "2026-03-19T02:14:08+08:00",
          "tree_id": "8dec9fc2b03ae13821e88d34f87d0029c2c6cd85",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/fac91df5f3d24cdad121065f2b782f025317268c"
        },
        "date": 1773857918356,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.4913511965373709,
            "unit": "iter/sec",
            "range": "stddev: 0.018252988075939718",
            "extra": "mean: 2.0352041616000065 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 191.9270523857568,
            "unit": "iter/sec",
            "range": "stddev: 0.00005847344457719956",
            "extra": "mean: 5.210312916128604 msec\nrounds: 155"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.835362726925498,
            "unit": "iter/sec",
            "range": "stddev: 0.01497347107543584",
            "extra": "mean: 101.67393188889504 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1558.7422326294147,
            "unit": "iter/sec",
            "range": "stddev: 0.000020296705785628536",
            "extra": "mean: 641.5428921259917 usec\nrounds: 1270"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 99.50010814000116,
            "unit": "iter/sec",
            "range": "stddev: 0.00023828049706142094",
            "extra": "mean: 10.050240333336669 msec\nrounds: 69"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5417.775257600885,
            "unit": "iter/sec",
            "range": "stddev: 0.0000115289301161539",
            "extra": "mean: 184.57760841907327 usec\nrounds: 3302"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.310910263757545,
            "unit": "iter/sec",
            "range": "stddev: 0.0004525905182527926",
            "extra": "mean: 61.308656833332975 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1729.5911191517698,
            "unit": "iter/sec",
            "range": "stddev: 0.000016374536760842157",
            "extra": "mean: 578.1713313204467 usec\nrounds: 1325"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 21.290391941309434,
            "unit": "iter/sec",
            "range": "stddev: 0.0008205137322336821",
            "extra": "mean: 46.96954394999722 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3831.5296372086864,
            "unit": "iter/sec",
            "range": "stddev: 0.00005590145078091903",
            "extra": "mean: 260.9923698067782 usec\nrounds: 2431"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 21.15035909007646,
            "unit": "iter/sec",
            "range": "stddev: 0.0007483714812612524",
            "extra": "mean: 47.28052113636171 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3842.1722125926963,
            "unit": "iter/sec",
            "range": "stddev: 0.00001308337367918218",
            "extra": "mean: 260.2694373569477 usec\nrounds: 2618"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.9231583561565095,
            "unit": "iter/sec",
            "range": "stddev: 0.015076609931344437",
            "extra": "mean: 144.4427454285712 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 754.412695161985,
            "unit": "iter/sec",
            "range": "stddev: 0.00002740072368776998",
            "extra": "mean: 1.3255344275261476 msec\nrounds: 683"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 7.328899274761667,
            "unit": "iter/sec",
            "range": "stddev: 0.00048819253233463024",
            "extra": "mean: 136.44613774999925 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 751.2645660806852,
            "unit": "iter/sec",
            "range": "stddev: 0.000020643687913994928",
            "extra": "mean: 1.3310890000003017 msec\nrounds: 688"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.954960862518355,
            "unit": "iter/sec",
            "range": "stddev: 0.001936252118963524",
            "extra": "mean: 201.8179411999938 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 65.85826971476554,
            "unit": "iter/sec",
            "range": "stddev: 0.00034548426790338244",
            "extra": "mean: 15.184121968752518 msec\nrounds: 64"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 1.0235586146409865,
            "unit": "iter/sec",
            "range": "stddev: 0.00041661218829411594",
            "extra": "mean: 976.9836193999993 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.3194731332906358,
            "unit": "iter/sec",
            "range": "stddev: 0.0006288457861897219",
            "extra": "mean: 757.8782581999974 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.481065764094301,
            "unit": "iter/sec",
            "range": "stddev: 0.018774194831893472",
            "extra": "mean: 675.1894643999947 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 20.49807967547291,
            "unit": "iter/sec",
            "range": "stddev: 0.0004562918562050289",
            "extra": "mean: 48.78505771428704 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5424649399584986,
            "unit": "iter/sec",
            "range": "stddev: 0.021442548366407882",
            "extra": "mean: 1.8434371078000082 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.8165359528205527,
            "unit": "iter/sec",
            "range": "stddev: 0.002345749660171685",
            "extra": "mean: 1.2246858164000116 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5039539337676606,
            "unit": "iter/sec",
            "range": "stddev: 0.018540966369471674",
            "extra": "mean: 1.9843083523999894 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.179836576206142,
            "unit": "iter/sec",
            "range": "stddev: 0.006953230684839164",
            "extra": "mean: 847.5750118000065 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.455824214099065,
            "unit": "iter/sec",
            "range": "stddev: 0.027496626159753523",
            "extra": "mean: 2.1938281667999946 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9903698892052535,
            "unit": "iter/sec",
            "range": "stddev: 0.002415977392239963",
            "extra": "mean: 1.009723751599995 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.335114271638771,
            "unit": "iter/sec",
            "range": "stddev: 0.01765003820045936",
            "extra": "mean: 157.8503491999868 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 79.66951426717559,
            "unit": "iter/sec",
            "range": "stddev: 0.0002440734133419964",
            "extra": "mean: 12.551852602570808 msec\nrounds: 78"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0906448034014276,
            "unit": "iter/sec",
            "range": "stddev: 0.002897163365514037",
            "extra": "mean: 916.8887953999956 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.2285255602178657,
            "unit": "iter/sec",
            "range": "stddev: 0.0013486440174564156",
            "extra": "mean: 448.727184400002 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "d6b9a8cfcf8671f58992aad19551c54d9a074b23",
          "message": "ci: disable GPMC static build on Linux to rely on auditwheel bundling",
          "timestamp": "2026-03-19T02:27:45+08:00",
          "tree_id": "cdaf6aeb254998fccb2429434b7d4515dae63dae",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/d6b9a8cfcf8671f58992aad19551c54d9a074b23"
        },
        "date": 1773858718275,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.4852854087722062,
            "unit": "iter/sec",
            "range": "stddev: 0.014618399784479737",
            "extra": "mean: 2.0606430399999964 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 192.34666171292253,
            "unit": "iter/sec",
            "range": "stddev: 0.00005683403999702624",
            "extra": "mean: 5.198946480768667 msec\nrounds: 156"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.865658895311153,
            "unit": "iter/sec",
            "range": "stddev: 0.012848152034205966",
            "extra": "mean: 101.36170433332836 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1589.8919066622784,
            "unit": "iter/sec",
            "range": "stddev: 0.00002430796206366967",
            "extra": "mean: 628.9735772662298 usec\nrounds: 1346"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 100.78865332582164,
            "unit": "iter/sec",
            "range": "stddev: 0.00014473034156795093",
            "extra": "mean: 9.921751774649458 msec\nrounds: 71"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5474.307801977089,
            "unit": "iter/sec",
            "range": "stddev: 0.00000954132562471428",
            "extra": "mean: 182.67149677605673 usec\nrounds: 3567"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.416459513573084,
            "unit": "iter/sec",
            "range": "stddev: 0.0011228283229684287",
            "extra": "mean: 60.91447423076838 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1737.0739968872635,
            "unit": "iter/sec",
            "range": "stddev: 0.00006305969396322827",
            "extra": "mean: 575.6807146914538 usec\nrounds: 1409"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 21.2329900499577,
            "unit": "iter/sec",
            "range": "stddev: 0.0006178722589858864",
            "extra": "mean: 47.09652279999972 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3787.736772701277,
            "unit": "iter/sec",
            "range": "stddev: 0.000011451150633328884",
            "extra": "mean: 264.00989826091745 usec\nrounds: 2703"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 21.164096350153287,
            "unit": "iter/sec",
            "range": "stddev: 0.0003562454790037539",
            "extra": "mean: 47.24983214285722 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3888.9703310832388,
            "unit": "iter/sec",
            "range": "stddev: 0.000009785131987556845",
            "extra": "mean: 257.13747209829154 usec\nrounds: 2688"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.873135290780359,
            "unit": "iter/sec",
            "range": "stddev: 0.01575446563065982",
            "extra": "mean: 145.49400785714235 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 762.1449878103925,
            "unit": "iter/sec",
            "range": "stddev: 0.00002058642150159682",
            "extra": "mean: 1.3120863037792245 msec\nrounds: 688"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 7.175446129214749,
            "unit": "iter/sec",
            "range": "stddev: 0.0010577201725317337",
            "extra": "mean: 139.3641568750006 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 762.1033576905144,
            "unit": "iter/sec",
            "range": "stddev: 0.000016237342826058056",
            "extra": "mean: 1.3121579768791598 msec\nrounds: 692"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.840655617854811,
            "unit": "iter/sec",
            "range": "stddev: 0.0011851683176475",
            "extra": "mean: 206.5835867999965 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 61.6186994003817,
            "unit": "iter/sec",
            "range": "stddev: 0.00028310502673382145",
            "extra": "mean: 16.22883977966282 msec\nrounds: 59"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 1.01767152366372,
            "unit": "iter/sec",
            "range": "stddev: 0.002598895429263822",
            "extra": "mean: 982.6353363999999 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.3169598049173,
            "unit": "iter/sec",
            "range": "stddev: 0.0005602588985343813",
            "extra": "mean: 759.3246173999944 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4717293908892848,
            "unit": "iter/sec",
            "range": "stddev: 0.01872771425608334",
            "extra": "mean: 679.4727388000013 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.437534225549456,
            "unit": "iter/sec",
            "range": "stddev: 0.0004987057035495871",
            "extra": "mean: 51.44685475000017 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5423407677816854,
            "unit": "iter/sec",
            "range": "stddev: 0.02129607293630715",
            "extra": "mean: 1.843859173800007 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.8163493612049294,
            "unit": "iter/sec",
            "range": "stddev: 0.007163200649648623",
            "extra": "mean: 1.224965740799996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4600556206380454,
            "unit": "iter/sec",
            "range": "stddev: 0.027501791894567213",
            "extra": "mean: 2.1736502177999966 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9742299339970643,
            "unit": "iter/sec",
            "range": "stddev: 0.010669866905008317",
            "extra": "mean: 1.0264517288000037 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.45287551113424407,
            "unit": "iter/sec",
            "range": "stddev: 0.027130866662047157",
            "extra": "mean: 2.2081123297999965 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9869259696220698,
            "unit": "iter/sec",
            "range": "stddev: 0.0026513269722686778",
            "extra": "mean: 1.0132472250000035 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.139222495637019,
            "unit": "iter/sec",
            "range": "stddev: 0.019264770101017962",
            "extra": "mean: 162.88707580001756 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 73.87400084395139,
            "unit": "iter/sec",
            "range": "stddev: 0.00033445569759672723",
            "extra": "mean: 13.53656210000541 msec\nrounds: 70"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0890775331439948,
            "unit": "iter/sec",
            "range": "stddev: 0.0022495083011424065",
            "extra": "mean: 918.2082722000132 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.227678224006311,
            "unit": "iter/sec",
            "range": "stddev: 0.00019684487450246933",
            "extra": "mean: 448.89786559998583 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "c8867dad2a47e7f09771bfa6507dbe47d6e4999d",
          "message": "update readme",
          "timestamp": "2026-09-24T14:32:34+08:00",
          "tree_id": "43e1fb4873f7e9e726a077662768b354f1520f0b",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/c8867dad2a47e7f09771bfa6507dbe47d6e4999d"
        },
        "date": 1790232326568,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.48427825625334653,
            "unit": "iter/sec",
            "range": "stddev: 0.030444740714349498",
            "extra": "mean: 2.064928555200004 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 100.85002383101116,
            "unit": "iter/sec",
            "range": "stddev: 0.0004021445586739788",
            "extra": "mean: 9.915714067412072 msec\nrounds: 89"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.71404958393692,
            "unit": "iter/sec",
            "range": "stddev: 0.01832836493589759",
            "extra": "mean: 102.94367877775636 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 473.6293196876471,
            "unit": "iter/sec",
            "range": "stddev: 0.00014282068632968679",
            "extra": "mean: 2.111355776410734 msec\nrounds: 407"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 101.50385010878136,
            "unit": "iter/sec",
            "range": "stddev: 0.00018089866997883478",
            "extra": "mean: 9.851843047611524 msec\nrounds: 63"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 1270.0714860539467,
            "unit": "iter/sec",
            "range": "stddev: 0.00010264802029485305",
            "extra": "mean: 787.3572558556949 usec\nrounds: 1110"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.36865538027278,
            "unit": "iter/sec",
            "range": "stddev: 0.001445090881628132",
            "extra": "mean: 61.09237299999502 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 587.2870565155656,
            "unit": "iter/sec",
            "range": "stddev: 0.00013264792208970334",
            "extra": "mean: 1.7027448313489195 msec\nrounds: 504"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 21.11337647435829,
            "unit": "iter/sec",
            "range": "stddev: 0.0003853608270157081",
            "extra": "mean: 47.3633386500012 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 830.3839260238487,
            "unit": "iter/sec",
            "range": "stddev: 0.001974574979669831",
            "extra": "mean: 1.2042622317947902 msec\nrounds: 824"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 21.076458283091196,
            "unit": "iter/sec",
            "range": "stddev: 0.0005296591180457565",
            "extra": "mean: 47.44630177273476 msec\nrounds: 22"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 829.8226713292895,
            "unit": "iter/sec",
            "range": "stddev: 0.002364335611086023",
            "extra": "mean: 1.2050767405500071 msec\nrounds: 794"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 7.10330589216005,
            "unit": "iter/sec",
            "range": "stddev: 0.001302838781183548",
            "extra": "mean: 140.77952085714125 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 267.75394306162605,
            "unit": "iter/sec",
            "range": "stddev: 0.00481932221324347",
            "extra": "mean: 3.7347722635398903 msec\nrounds: 277"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.576589296479367,
            "unit": "iter/sec",
            "range": "stddev: 0.001020495695638391",
            "extra": "mean: 152.05450042856228 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 271.5323864269797,
            "unit": "iter/sec",
            "range": "stddev: 0.0043366688368204264",
            "extra": "mean: 3.682801941818897 msec\nrounds: 275"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.799622674399209,
            "unit": "iter/sec",
            "range": "stddev: 0.0014186765985002255",
            "extra": "mean: 208.3497116000217 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 53.6327999246255,
            "unit": "iter/sec",
            "range": "stddev: 0.000584766708194149",
            "extra": "mean: 18.64530662962554 msec\nrounds: 54"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 1.0161809636879595,
            "unit": "iter/sec",
            "range": "stddev: 0.005552989767418798",
            "extra": "mean: 984.0766907999978 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.310435487073991,
            "unit": "iter/sec",
            "range": "stddev: 0.001554491393461756",
            "extra": "mean: 763.1050973999891 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4020727538631321,
            "unit": "iter/sec",
            "range": "stddev: 0.030569608698009378",
            "extra": "mean: 713.2297501999801 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 18.30615091362906,
            "unit": "iter/sec",
            "range": "stddev: 0.00101591771824055",
            "extra": "mean: 54.626447947366856 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5339127006561725,
            "unit": "iter/sec",
            "range": "stddev: 0.0338087437665866",
            "extra": "mean: 1.872965371999976 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.8139383659461964,
            "unit": "iter/sec",
            "range": "stddev: 0.0032614301666580754",
            "extra": "mean: 1.2285942545999888 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4426354196098211,
            "unit": "iter/sec",
            "range": "stddev: 0.035577649069700144",
            "extra": "mean: 2.259195617200021 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9514151920225395,
            "unit": "iter/sec",
            "range": "stddev: 0.005784897689066982",
            "extra": "mean: 1.0510658315999535 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.4403798493713194,
            "unit": "iter/sec",
            "range": "stddev: 0.038668333803559905",
            "extra": "mean: 2.270766933200025 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9637863395256288,
            "unit": "iter/sec",
            "range": "stddev: 0.0371171984114346",
            "extra": "mean: 1.0375743657999918 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.24010116372156,
            "unit": "iter/sec",
            "range": "stddev: 0.002219066213314955",
            "extra": "mean: 160.25381219999417 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 63.611737048146075,
            "unit": "iter/sec",
            "range": "stddev: 0.00039658470892441625",
            "extra": "mean: 15.720369328118267 msec\nrounds: 64"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0805435689465304,
            "unit": "iter/sec",
            "range": "stddev: 0.00498546472345272",
            "extra": "mean: 925.4601375999528 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.2183062658893675,
            "unit": "iter/sec",
            "range": "stddev: 0.0014362225866954813",
            "extra": "mean: 450.7943809999915 msec\nrounds: 5"
          }
        ]
      },
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
          "id": "cae287b5130244dccb72d36ed59af678a6e29b18",
          "message": "chore: bump version to 0.13.1 and optimize rust backend entry point",
          "timestamp": "2026-09-24T15:15:12+08:00",
          "tree_id": "b6720a4eda8fdc4ff0fe7327d89bbfffc7afb2a7",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/cae287b5130244dccb72d36ed59af678a6e29b18"
        },
        "date": 1790234364932,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.4671968195907686,
            "unit": "iter/sec",
            "range": "stddev: 0.029496750210934376",
            "extra": "mean: 2.140425529599986 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 182.19016822286832,
            "unit": "iter/sec",
            "range": "stddev: 0.00017716229431261215",
            "extra": "mean: 5.488770386208365 msec\nrounds: 145"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.617350080391711,
            "unit": "iter/sec",
            "range": "stddev: 0.0009338193025596516",
            "extra": "mean: 103.97874587500411 msec\nrounds: 8"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1546.7090326962866,
            "unit": "iter/sec",
            "range": "stddev: 0.00002024969439027788",
            "extra": "mean: 646.5340143884458 usec\nrounds: 1251"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 92.39429574054854,
            "unit": "iter/sec",
            "range": "stddev: 0.00028855562029774434",
            "extra": "mean: 10.823178985075979 msec\nrounds: 67"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5366.6931215800905,
            "unit": "iter/sec",
            "range": "stddev: 0.000017599503573565963",
            "extra": "mean: 186.33448519329062 usec\nrounds: 2904"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 14.200349190847316,
            "unit": "iter/sec",
            "range": "stddev: 0.01892754469953979",
            "extra": "mean: 70.42080349999698 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1720.4822194483907,
            "unit": "iter/sec",
            "range": "stddev: 0.00001976726768025173",
            "extra": "mean: 581.2323944391667 usec\nrounds: 1151"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.13694775704488,
            "unit": "iter/sec",
            "range": "stddev: 0.0005877140551264846",
            "extra": "mean: 49.65995900000047 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3712.3124276800972,
            "unit": "iter/sec",
            "range": "stddev: 0.000046832766015183205",
            "extra": "mean: 269.37387934908304 usec\nrounds: 2213"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 20.183061598907088,
            "unit": "iter/sec",
            "range": "stddev: 0.0005813833418494874",
            "extra": "mean: 49.54649695238258 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3563.4360292554493,
            "unit": "iter/sec",
            "range": "stddev: 0.000013261843072684185",
            "extra": "mean: 280.6280207614508 usec\nrounds: 2312"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.582295616406913,
            "unit": "iter/sec",
            "range": "stddev: 0.0010391647231626842",
            "extra": "mean: 151.92268142856082 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 738.435275388174,
            "unit": "iter/sec",
            "range": "stddev: 0.000020302801819616284",
            "extra": "mean: 1.354214828746269 msec\nrounds: 654"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.242014167709994,
            "unit": "iter/sec",
            "range": "stddev: 0.023476341093367662",
            "extra": "mean: 160.20469885714306 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 736.617925793561,
            "unit": "iter/sec",
            "range": "stddev: 0.000023883322884315518",
            "extra": "mean: 1.357555884786128 msec\nrounds: 677"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.419055474158549,
            "unit": "iter/sec",
            "range": "stddev: 0.0028905623060893957",
            "extra": "mean: 226.29270120000342 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 56.86439884854839,
            "unit": "iter/sec",
            "range": "stddev: 0.00028232592927985125",
            "extra": "mean: 17.58569544827831 msec\nrounds: 58"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 0.9947723091684714,
            "unit": "iter/sec",
            "range": "stddev: 0.021993055374860827",
            "extra": "mean: 1.0052551632000075 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 1.3049178316703822,
            "unit": "iter/sec",
            "range": "stddev: 0.00945429986475724",
            "extra": "mean: 766.3317763999999 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4108158694703254,
            "unit": "iter/sec",
            "range": "stddev: 0.006645532879516186",
            "extra": "mean: 708.8097189999985 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 18.864410924988835,
            "unit": "iter/sec",
            "range": "stddev: 0.0006040379532832304",
            "extra": "mean: 53.009871549996035 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 0.5313259116089247,
            "unit": "iter/sec",
            "range": "stddev: 0.01523712576386666",
            "extra": "mean: 1.8820840056000065 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 0.81460020658017,
            "unit": "iter/sec",
            "range": "stddev: 0.0028418946411728463",
            "extra": "mean: 1.227596054999998 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4485452425714225,
            "unit": "iter/sec",
            "range": "stddev: 0.02651674337014248",
            "extra": "mean: 2.229429509199997 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9673174434512568,
            "unit": "iter/sec",
            "range": "stddev: 0.0071227454422627835",
            "extra": "mean: 1.0337867954000046 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.4416316416038489,
            "unit": "iter/sec",
            "range": "stddev: 0.03466348194544126",
            "extra": "mean: 2.264330509399997 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 0.9848584356044436,
            "unit": "iter/sec",
            "range": "stddev: 0.004949006252759319",
            "extra": "mean: 1.0153743561999988 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.247735851766023,
            "unit": "iter/sec",
            "range": "stddev: 0.0011774411855335531",
            "extra": "mean: 160.0579831999994 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 72.3897532651695,
            "unit": "iter/sec",
            "range": "stddev: 0.0005562271242211029",
            "extra": "mean: 13.814109800000551 msec\nrounds: 70"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 1.0881176385880766,
            "unit": "iter/sec",
            "range": "stddev: 0.002182409961913074",
            "extra": "mean: 919.0182793999952 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 2.2240705009211297,
            "unit": "iter/sec",
            "range": "stddev: 0.00045668031899150243",
            "extra": "mean: 449.62603459999855 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "1f19c5cf2b3ed7f0d5e6540f8920baaae9bd18f4",
          "message": "fix: upgrade Ganak to 2.8.0 and harden WMC validation (#24)\n\nPin Ganak 2.8.0 with platform diagnostics, independent solver modes, numeric and failure validation, lazy Rust-path verification, regression tests, and v0.13.2 changelog.",
          "timestamp": "2026-10-16T17:39:36+08:00",
          "tree_id": "1dabab9e8d5f844ae09b47546b759195ecfc90d6",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/1f19c5cf2b3ed7f0d5e6540f8920baaae9bd18f4"
        },
        "date": 1792143772286,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.7196297802304473,
            "unit": "iter/sec",
            "range": "stddev: 0.009497551200563314",
            "extra": "mean: 1.3896034147999956 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 239.2165694391231,
            "unit": "iter/sec",
            "range": "stddev: 0.00006038543237784058",
            "extra": "mean: 4.180312435483214 msec\nrounds: 186"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 14.311582761195814,
            "unit": "iter/sec",
            "range": "stddev: 0.014779202481279102",
            "extra": "mean: 69.87347358332603 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2154.9259672662797,
            "unit": "iter/sec",
            "range": "stddev: 0.00001224025950053626",
            "extra": "mean: 464.0530650194871 usec\nrounds: 1538"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 150.92296257786134,
            "unit": "iter/sec",
            "range": "stddev: 0.00012646151846206207",
            "extra": "mean: 6.625896967031102 msec\nrounds: 91"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 8388.813612130323,
            "unit": "iter/sec",
            "range": "stddev: 0.000009096720171750979",
            "extra": "mean: 119.2063676982867 usec\nrounds: 3715"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 23.855742828155876,
            "unit": "iter/sec",
            "range": "stddev: 0.00039025001160784275",
            "extra": "mean: 41.91862761111528 msec\nrounds: 18"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2371.1925679682745,
            "unit": "iter/sec",
            "range": "stddev: 0.00003754053515841368",
            "extra": "mean: 421.72871723229 usec\nrounds: 1503"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 30.395343923110296,
            "unit": "iter/sec",
            "range": "stddev: 0.00046546606126139975",
            "extra": "mean: 32.89977578571422 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 5524.917457344008,
            "unit": "iter/sec",
            "range": "stddev: 0.00003633013139173644",
            "extra": "mean: 180.99817919826984 usec\nrounds: 3019"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 29.906346673956925,
            "unit": "iter/sec",
            "range": "stddev: 0.001654913498750109",
            "extra": "mean: 33.437718451609506 msec\nrounds: 31"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 5535.291755297965,
            "unit": "iter/sec",
            "range": "stddev: 0.000008055206627535975",
            "extra": "mean: 180.6589506402937 usec\nrounds: 2654"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 9.661269794408046,
            "unit": "iter/sec",
            "range": "stddev: 0.0194183831563789",
            "extra": "mean: 103.50606300000038 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 934.840368547723,
            "unit": "iter/sec",
            "range": "stddev: 0.0000154148667969871",
            "extra": "mean: 1.0697013454323787 msec\nrounds: 799"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 10.29257697075071,
            "unit": "iter/sec",
            "range": "stddev: 0.001426460701779262",
            "extra": "mean: 97.1573982727343 msec\nrounds: 11"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 933.4504604523905,
            "unit": "iter/sec",
            "range": "stddev: 0.00001952230718608928",
            "extra": "mean: 1.0712941311479525 msec\nrounds: 793"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 6.163709866948969,
            "unit": "iter/sec",
            "range": "stddev: 0.02458025512139122",
            "extra": "mean: 162.2399531428625 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 70.52107940950808,
            "unit": "iter/sec",
            "range": "stddev: 0.00027034792939659413",
            "extra": "mean: 14.180157314284868 msec\nrounds: 70"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 3.4472767485473357,
            "unit": "iter/sec",
            "range": "stddev: 0.006023586374866373",
            "extra": "mean: 290.08404980000364 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 6.573172559562085,
            "unit": "iter/sec",
            "range": "stddev: 0.0004656116568988001",
            "extra": "mean: 152.13353840000536 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.8610494026934796,
            "unit": "iter/sec",
            "range": "stddev: 0.04664370206855924",
            "extra": "mean: 537.3312490000046 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 23.395061997246987,
            "unit": "iter/sec",
            "range": "stddev: 0.0004705672306615899",
            "extra": "mean: 42.74406283333102 msec\nrounds: 24"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.3482730512088434,
            "unit": "iter/sec",
            "range": "stddev: 0.022668028317127404",
            "extra": "mean: 741.6895257999954 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 4.041416945223487,
            "unit": "iter/sec",
            "range": "stddev: 0.0008802169608712309",
            "extra": "mean: 247.4379687999999 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5670763898832928,
            "unit": "iter/sec",
            "range": "stddev: 0.024055624921959978",
            "extra": "mean: 1.7634308496000073 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1287623488122105,
            "unit": "iter/sec",
            "range": "stddev: 0.030233647542250632",
            "extra": "mean: 885.9260773999893 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.8636099379338082,
            "unit": "iter/sec",
            "range": "stddev: 0.03359321236270533",
            "extra": "mean: 1.1579301674000022 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.9921087933067896,
            "unit": "iter/sec",
            "range": "stddev: 0.005920466921344749",
            "extra": "mean: 501.9806163999988 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 8.881392062428462,
            "unit": "iter/sec",
            "range": "stddev: 0.001773073117738298",
            "extra": "mean: 112.59496180000497 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 88.1741184141489,
            "unit": "iter/sec",
            "range": "stddev: 0.00032552413529207116",
            "extra": "mean: 11.341196464285087 msec\nrounds: 84"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 4.10066263665516,
            "unit": "iter/sec",
            "range": "stddev: 0.00034180861036718315",
            "extra": "mean: 243.86302620000038 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 10.529569103890221,
            "unit": "iter/sec",
            "range": "stddev: 0.0013667720517118393",
            "extra": "mean: 94.9706479090909 msec\nrounds: 11"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "18f773f6fada887b9ffb82ce0d70328028cf0598",
          "message": "fix: preserve WMC input precision and align Python/Rust numeric checks (#30)\n\nPreserve Rust f64 WMC weights and Python 113-bit phase weights; align normalized magnitude/phase decisions and cover numerical boundaries. Keep solver adapters independent. Report noisy shared-runner performance comparisons without suppressing correctness failures.",
          "timestamp": "2026-10-16T21:09:11+08:00",
          "tree_id": "6ae72d26e398fc98b8dc4c5829de38bfcc2c1ced",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/18f773f6fada887b9ffb82ce0d70328028cf0598"
        },
        "date": 1792156363139,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.4835316470221761,
            "unit": "iter/sec",
            "range": "stddev: 0.0075620017206682",
            "extra": "mean: 2.0681169601999954 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 194.15228317965912,
            "unit": "iter/sec",
            "range": "stddev: 0.00004292146477894281",
            "extra": "mean: 5.150596138365514 msec\nrounds: 159"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.652586850428651,
            "unit": "iter/sec",
            "range": "stddev: 0.014544312905957818",
            "extra": "mean: 103.59917144444984 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1594.5903344422154,
            "unit": "iter/sec",
            "range": "stddev: 0.00001415185535392609",
            "extra": "mean: 627.1203194956014 usec\nrounds: 1349"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 98.86378112121143,
            "unit": "iter/sec",
            "range": "stddev: 0.00024309148018922128",
            "extra": "mean: 10.114927718311272 msec\nrounds: 71"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5287.672176116887,
            "unit": "iter/sec",
            "range": "stddev: 0.000011863451462872052",
            "extra": "mean: 189.11913724847648 usec\nrounds: 3031"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.456490360121137,
            "unit": "iter/sec",
            "range": "stddev: 0.0004773718204827782",
            "extra": "mean: 60.766298166666864 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1735.4654517141282,
            "unit": "iter/sec",
            "range": "stddev: 0.000014494930994811217",
            "extra": "mean: 576.2142939879874 usec\nrounds: 1364"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.487697210070696,
            "unit": "iter/sec",
            "range": "stddev: 0.0005282625198723259",
            "extra": "mean: 48.80978031579125 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3811.8742740805806,
            "unit": "iter/sec",
            "range": "stddev: 0.00004266568548818857",
            "extra": "mean: 262.3381381698899 usec\nrounds: 2591"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 20.766248626392336,
            "unit": "iter/sec",
            "range": "stddev: 0.0004991906199655036",
            "extra": "mean: 48.155062476189144 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3842.9626362643476,
            "unit": "iter/sec",
            "range": "stddev: 0.000013545015281865081",
            "extra": "mean: 260.21590492799487 usec\nrounds: 2577"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.93220661709915,
            "unit": "iter/sec",
            "range": "stddev: 0.0007048805899182498",
            "extra": "mean: 144.25421157144618 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 751.1362260309039,
            "unit": "iter/sec",
            "range": "stddev: 0.0001072468336175719",
            "extra": "mean: 1.3313164314868993 msec\nrounds: 686"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.697203570928787,
            "unit": "iter/sec",
            "range": "stddev: 0.016156426725553886",
            "extra": "mean: 149.31605250000146 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 743.3977891111073,
            "unit": "iter/sec",
            "range": "stddev: 0.000022388839141958593",
            "extra": "mean: 1.3451748372775174 msec\nrounds: 676"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.74680476005254,
            "unit": "iter/sec",
            "range": "stddev: 0.004390728355252838",
            "extra": "mean: 210.66802839999923 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 55.243414098433135,
            "unit": "iter/sec",
            "range": "stddev: 0.0002740239162768689",
            "extra": "mean: 18.10170526785677 msec\nrounds: 56"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.6131145670611495,
            "unit": "iter/sec",
            "range": "stddev: 0.02133935679889504",
            "extra": "mean: 382.68509639998456 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.471583156690769,
            "unit": "iter/sec",
            "range": "stddev: 0.00022437690132145064",
            "extra": "mean: 182.76246039999933 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4635003974113387,
            "unit": "iter/sec",
            "range": "stddev: 0.025174527994661525",
            "extra": "mean: 683.2932889999995 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.54440105337655,
            "unit": "iter/sec",
            "range": "stddev: 0.00045440782449496556",
            "extra": "mean: 51.16554850000057 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0668869813888486,
            "unit": "iter/sec",
            "range": "stddev: 0.0316637393669202",
            "extra": "mean: 937.3064040000031 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.3318958579459106,
            "unit": "iter/sec",
            "range": "stddev: 0.0003805995516076894",
            "extra": "mean: 300.1294285999961 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4564220546525952,
            "unit": "iter/sec",
            "range": "stddev: 0.016293241480415884",
            "extra": "mean: 2.1909545996000306 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9497418228287147,
            "unit": "iter/sec",
            "range": "stddev: 0.012428849446553435",
            "extra": "mean: 1.052917725599991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6688087387093421,
            "unit": "iter/sec",
            "range": "stddev: 0.031018873347326146",
            "extra": "mean: 1.4951957743999968 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6228269692476498,
            "unit": "iter/sec",
            "range": "stddev: 0.0009625408788230722",
            "extra": "mean: 616.2086402000114 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.237395401202693,
            "unit": "iter/sec",
            "range": "stddev: 0.0029781385227728094",
            "extra": "mean: 160.32332979999637 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 71.6276809617875,
            "unit": "iter/sec",
            "range": "stddev: 0.0005849391428325445",
            "extra": "mean: 13.961083013890788 msec\nrounds: 72"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.0184227033068156,
            "unit": "iter/sec",
            "range": "stddev: 0.02706002047938473",
            "extra": "mean: 331.2988598000061 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.671232149397845,
            "unit": "iter/sec",
            "range": "stddev: 0.000680605555846876",
            "extra": "mean: 115.32386433333386 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "feb645cdac4e24d9786c0f9c638c70e708c0af63",
          "message": "fix(wmc): isolate parallel solver CNF inputs (#32)\n\nCreate solver CNF files exclusively with process-unique identifiers and add parallel Ganak fixture regression tests. Preserve solver selection and numerical tolerances.",
          "timestamp": "2026-10-16T21:36:14+08:00",
          "tree_id": "cf75b01d9665a92c7b094a433b7c46dde9f07945",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/feb645cdac4e24d9786c0f9c638c70e708c0af63"
        },
        "date": 1792157983471,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.5643399795009374,
            "unit": "iter/sec",
            "range": "stddev: 0.0045172540595315525",
            "extra": "mean: 1.7719814939999992 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 195.7193997448256,
            "unit": "iter/sec",
            "range": "stddev: 0.00003808141561859137",
            "extra": "mean: 5.109355543210213 msec\nrounds: 162"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 11.389851971743152,
            "unit": "iter/sec",
            "range": "stddev: 0.014416887159755276",
            "extra": "mean: 87.79745360000106 msec\nrounds: 10"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1760.6955823809585,
            "unit": "iter/sec",
            "range": "stddev: 0.00005508787025504458",
            "extra": "mean: 567.9573516324253 usec\nrounds: 1348"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 121.20210358718809,
            "unit": "iter/sec",
            "range": "stddev: 0.00015585813676246156",
            "extra": "mean: 8.250681880951339 msec\nrounds: 84"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 6765.8852175072725,
            "unit": "iter/sec",
            "range": "stddev: 0.000004608269223202667",
            "extra": "mean: 147.80031996588113 usec\nrounds: 3466"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 18.732818212305123,
            "unit": "iter/sec",
            "range": "stddev: 0.0005001547661648326",
            "extra": "mean: 53.382250799995745 msec\nrounds: 15"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1900.6254119170123,
            "unit": "iter/sec",
            "range": "stddev: 0.00001240703513929722",
            "extra": "mean: 526.1426021823933 usec\nrounds: 1375"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 24.325186976637532,
            "unit": "iter/sec",
            "range": "stddev: 0.0002931642386458847",
            "extra": "mean: 41.10965317390666 msec\nrounds: 23"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 4653.334190183262,
            "unit": "iter/sec",
            "range": "stddev: 0.00004133279870748833",
            "extra": "mean: 214.89967389610956 usec\nrounds: 2628"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 24.351795837946444,
            "unit": "iter/sec",
            "range": "stddev: 0.00041406756902804306",
            "extra": "mean: 41.064733239991256 msec\nrounds: 25"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 4632.228989446007,
            "unit": "iter/sec",
            "range": "stddev: 0.000005910996105714943",
            "extra": "mean: 215.87879232187854 usec\nrounds: 2865"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 7.8203305565549375,
            "unit": "iter/sec",
            "range": "stddev: 0.0178198542126",
            "extra": "mean: 127.87183262500434 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 735.5779991891735,
            "unit": "iter/sec",
            "range": "stddev: 0.000013993328743677416",
            "extra": "mean: 1.3594751353388743 msec\nrounds: 665"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 8.220455856336939,
            "unit": "iter/sec",
            "range": "stddev: 0.0004605999449566443",
            "extra": "mean: 121.64775500000108 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 728.5433331391189,
            "unit": "iter/sec",
            "range": "stddev: 0.00009370891696679737",
            "extra": "mean: 1.372601950375744 msec\nrounds: 665"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 5.211664107865106,
            "unit": "iter/sec",
            "range": "stddev: 0.0009206587909032537",
            "extra": "mean: 191.87729279998393 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 56.57199957352777,
            "unit": "iter/sec",
            "range": "stddev: 0.00036092402623262934",
            "extra": "mean: 17.676589258618655 msec\nrounds: 58"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.710650206028616,
            "unit": "iter/sec",
            "range": "stddev: 0.0028194074971384835",
            "extra": "mean: 368.9151767999988 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.23985931258637,
            "unit": "iter/sec",
            "range": "stddev: 0.0029956417082451677",
            "extra": "mean: 190.84481859998732 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4960579025369791,
            "unit": "iter/sec",
            "range": "stddev: 0.022392686096563006",
            "extra": "mean: 668.4233266000092 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.333029673944747,
            "unit": "iter/sec",
            "range": "stddev: 0.0013895769046347566",
            "extra": "mean: 51.72495035000679 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0798682498793815,
            "unit": "iter/sec",
            "range": "stddev: 0.016909881013855474",
            "extra": "mean: 926.0388942000077 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.1938264387622404,
            "unit": "iter/sec",
            "range": "stddev: 0.0006190482562894512",
            "extra": "mean: 313.10405220001485 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4746574722851148,
            "unit": "iter/sec",
            "range": "stddev: 0.023947046639283688",
            "extra": "mean: 2.1067823817999964 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9968177969434711,
            "unit": "iter/sec",
            "range": "stddev: 0.007974042822842003",
            "extra": "mean: 1.0031923618000065 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6761600347844003,
            "unit": "iter/sec",
            "range": "stddev: 0.0025111868452408724",
            "extra": "mean: 1.478939819799996 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.5753238117399309,
            "unit": "iter/sec",
            "range": "stddev: 0.0027110802709482025",
            "extra": "mean: 634.7901254000021 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.374158602139907,
            "unit": "iter/sec",
            "range": "stddev: 0.01996955385540393",
            "extra": "mean: 156.8834512000194 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 72.77989240041755,
            "unit": "iter/sec",
            "range": "stddev: 0.0004770022176236299",
            "extra": "mean: 13.740058785718443 msec\nrounds: 70"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.1715166807470467,
            "unit": "iter/sec",
            "range": "stddev: 0.0016743851457593883",
            "extra": "mean: 315.30655540000225 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.472617134044096,
            "unit": "iter/sec",
            "range": "stddev: 0.0017588376070385152",
            "extra": "mean: 118.02728533334378 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cc9c53768ef2f69e9b0e5174efddbc5fd97d221a",
          "message": "ci(benchmark): authenticate provenance and report integrity (#26)\n\n* ci(benchmark): record baseline provenance and scope solver cache by source\n\n* ci(benchmark): invalidate GPMC cache on submodule updates and record runner CPU\n\n* ci(benchmark): preserve main report-only performance policy\n\n* ci(benchmark): report all provenance mismatches independently\n\n* ci(benchmark): include provenance and execution status in PR report\n\n* ci(benchmark): pass benchmark outcome and provenance into report",
          "timestamp": "2026-10-17T17:22:24+08:00",
          "tree_id": "804fa1aa66a85f013d19a3bc8e5d40a8f967990e",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/cc9c53768ef2f69e9b0e5174efddbc5fd97d221a"
        },
        "date": 1792229180440,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.48120939638182003,
            "unit": "iter/sec",
            "range": "stddev: 0.0037143323787887845",
            "extra": "mean: 2.078097409400004 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 192.38332110338982,
            "unit": "iter/sec",
            "range": "stddev: 0.00005899605338194173",
            "extra": "mean: 5.197955801285832 msec\nrounds: 156"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.46066517009509,
            "unit": "iter/sec",
            "range": "stddev: 0.01953225638520003",
            "extra": "mean: 105.7008130000175 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1549.7441944249786,
            "unit": "iter/sec",
            "range": "stddev: 0.000018844403525716694",
            "extra": "mean: 645.2677826426979 usec\nrounds: 1302"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 99.49661258383769,
            "unit": "iter/sec",
            "range": "stddev: 0.000221039429201101",
            "extra": "mean: 10.050593422538697 msec\nrounds: 71"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5248.055893215568,
            "unit": "iter/sec",
            "range": "stddev: 0.00001250404997053291",
            "extra": "mean: 190.5467510917236 usec\nrounds: 3206"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.199833193555744,
            "unit": "iter/sec",
            "range": "stddev: 0.0005877744765069638",
            "extra": "mean: 61.729030666673644 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1680.067722106884,
            "unit": "iter/sec",
            "range": "stddev: 0.000016553506522749815",
            "extra": "mean: 595.2141016946347 usec\nrounds: 1298"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.51015156914375,
            "unit": "iter/sec",
            "range": "stddev: 0.0009137741723751422",
            "extra": "mean: 48.75634373684677 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3629.683582342221,
            "unit": "iter/sec",
            "range": "stddev: 0.00004467352815585661",
            "extra": "mean: 275.506108814781 usec\nrounds: 2564"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 20.55368223695292,
            "unit": "iter/sec",
            "range": "stddev: 0.00032382534054786836",
            "extra": "mean: 48.65308261904168 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3858.5927661081773,
            "unit": "iter/sec",
            "range": "stddev: 0.000017302614410408298",
            "extra": "mean: 259.16183972132717 usec\nrounds: 2583"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.982031699529634,
            "unit": "iter/sec",
            "range": "stddev: 0.0006233927380991556",
            "extra": "mean: 143.22478657141704 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 734.9718750645292,
            "unit": "iter/sec",
            "range": "stddev: 0.00001764447998453478",
            "extra": "mean: 1.3605962812008308 msec\nrounds: 665"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.990635472881657,
            "unit": "iter/sec",
            "range": "stddev: 0.002585315231139141",
            "extra": "mean: 143.0485116666773 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 732.6927635976115,
            "unit": "iter/sec",
            "range": "stddev: 0.000026035842936671605",
            "extra": "mean: 1.3648285470841517 msec\nrounds: 669"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.779645549821839,
            "unit": "iter/sec",
            "range": "stddev: 0.0007531402299744507",
            "extra": "mean: 209.22053519999508 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 53.90385893829022,
            "unit": "iter/sec",
            "range": "stddev: 0.000854999498261583",
            "extra": "mean: 18.55154750877506 msec\nrounds: 57"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.5834594426669657,
            "unit": "iter/sec",
            "range": "stddev: 0.030984548580493685",
            "extra": "mean: 387.07787840000947 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.417726745132724,
            "unit": "iter/sec",
            "range": "stddev: 0.0018566769336627496",
            "extra": "mean: 184.57926119998547 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4246514143187905,
            "unit": "iter/sec",
            "range": "stddev: 0.03055077129492025",
            "extra": "mean: 701.9260922000058 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.444151726243664,
            "unit": "iter/sec",
            "range": "stddev: 0.0003553518744650813",
            "extra": "mean: 51.42934564999848 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.062632484621541,
            "unit": "iter/sec",
            "range": "stddev: 0.004825115902363089",
            "extra": "mean: 941.0591285999999 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.298219157503104,
            "unit": "iter/sec",
            "range": "stddev: 0.0048378207462701425",
            "extra": "mean: 303.193921400009 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4524712293544475,
            "unit": "iter/sec",
            "range": "stddev: 0.016720360949860347",
            "extra": "mean: 2.2100852720000033 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9447137361340979,
            "unit": "iter/sec",
            "range": "stddev: 0.012167628515037889",
            "extra": "mean: 1.0585217106000187 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6658557174371676,
            "unit": "iter/sec",
            "range": "stddev: 0.03633478539918412",
            "extra": "mean: 1.501826858000004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6134836552117573,
            "unit": "iter/sec",
            "range": "stddev: 0.004714816284322853",
            "extra": "mean: 619.7769632000131 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.298508990498824,
            "unit": "iter/sec",
            "range": "stddev: 0.001584197634146617",
            "extra": "mean: 158.76773399998 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 71.06843163626482,
            "unit": "iter/sec",
            "range": "stddev: 0.0003581997901037279",
            "extra": "mean: 14.070945101449512 msec\nrounds: 69"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.013008485767137,
            "unit": "iter/sec",
            "range": "stddev: 0.026386034392606346",
            "extra": "mean: 331.8941864000067 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.538178060003435,
            "unit": "iter/sec",
            "range": "stddev: 0.0036784684330390493",
            "extra": "mean: 117.12100555555732 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "25a080279f306ac01e8aba656e04762a14f42a92",
          "message": "fix(ci): avoid benchmark baseline checkout collision (#35)\n\nGenerate benchmark provenance outside the checkout before switching to the benchmarks branch, preventing untracked file overwrite conflicts. Preserve baseline publishing and test gates.",
          "timestamp": "2026-10-19T14:40:03+08:00",
          "tree_id": "dfa7daccdbd13a2a42a1a4b36bf8c59a8d59bf4c",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/25a080279f306ac01e8aba656e04762a14f42a92"
        },
        "date": 1792392230926,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.480260586643378,
            "unit": "iter/sec",
            "range": "stddev: 0.005584585248998034",
            "extra": "mean: 2.082202928600009 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 186.15329192184842,
            "unit": "iter/sec",
            "range": "stddev: 0.00015491359490842006",
            "extra": "mean: 5.371916820143174 msec\nrounds: 139"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.942967733657833,
            "unit": "iter/sec",
            "range": "stddev: 0.0026563293284877897",
            "extra": "mean: 100.57359399999972 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1538.9567650538852,
            "unit": "iter/sec",
            "range": "stddev: 0.000017253972223982167",
            "extra": "mean: 649.7908340946706 usec\nrounds: 1314"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 99.42530883165409,
            "unit": "iter/sec",
            "range": "stddev: 0.00010721582432770775",
            "extra": "mean: 10.05780129577661 msec\nrounds: 71"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5155.017981850815,
            "unit": "iter/sec",
            "range": "stddev: 0.000012006035761223211",
            "extra": "mean: 193.9857442826937 usec\nrounds: 3367"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.12299413174979,
            "unit": "iter/sec",
            "range": "stddev: 0.0007424749374277608",
            "extra": "mean: 62.023219250001205 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1676.1724841953262,
            "unit": "iter/sec",
            "range": "stddev: 0.000016802148754635982",
            "extra": "mean: 596.5973128833851 usec\nrounds: 1304"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.22527830435309,
            "unit": "iter/sec",
            "range": "stddev: 0.001751567298919754",
            "extra": "mean: 49.44307736842216 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3292.1457484484,
            "unit": "iter/sec",
            "range": "stddev: 0.00004413795215234501",
            "extra": "mean: 303.75325894101246 usec\nrounds: 2209"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 18.841353392741272,
            "unit": "iter/sec",
            "range": "stddev: 0.00042165310425216346",
            "extra": "mean: 53.07474357894349 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3533.8912694789005,
            "unit": "iter/sec",
            "range": "stddev: 0.000018426021440164134",
            "extra": "mean: 282.97418447383575 usec\nrounds: 2499"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.642127251625755,
            "unit": "iter/sec",
            "range": "stddev: 0.016261071606112423",
            "extra": "mean: 150.55417671428017 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 729.632570904034,
            "unit": "iter/sec",
            "range": "stddev: 0.00003366794467955259",
            "extra": "mean: 1.3705528506779427 msec\nrounds: 663"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.9478648479812275,
            "unit": "iter/sec",
            "range": "stddev: 0.0008389825258242712",
            "extra": "mean: 143.9291094285693 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 725.4641414478731,
            "unit": "iter/sec",
            "range": "stddev: 0.000022011763213726376",
            "extra": "mean: 1.3784278820510845 msec\nrounds: 585"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.543357360609094,
            "unit": "iter/sec",
            "range": "stddev: 0.005688221492458574",
            "extra": "mean: 220.1015506000033 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 40.85487795808177,
            "unit": "iter/sec",
            "range": "stddev: 0.00005922383437598909",
            "extra": "mean: 24.476881341464967 msec\nrounds: 41"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.6280800433203577,
            "unit": "iter/sec",
            "range": "stddev: 0.0018173162664793367",
            "extra": "mean: 380.50591439999835 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.36565394366204,
            "unit": "iter/sec",
            "range": "stddev: 0.00004846788641374042",
            "extra": "mean: 186.37057299999924 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.3812906434947445,
            "unit": "iter/sec",
            "range": "stddev: 0.016282606489423243",
            "extra": "mean: 723.9605977999986 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 17.639705245464967,
            "unit": "iter/sec",
            "range": "stddev: 0.00015873685642479586",
            "extra": "mean: 56.69028966666505 msec\nrounds: 18"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.031490824444955,
            "unit": "iter/sec",
            "range": "stddev: 0.021731617273787952",
            "extra": "mean: 969.4705724000016 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.2350186074776195,
            "unit": "iter/sec",
            "range": "stddev: 0.0003715383528063404",
            "extra": "mean: 309.11723280000274 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4472484262324576,
            "unit": "iter/sec",
            "range": "stddev: 0.017370090127868276",
            "extra": "mean: 2.235893837399999 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9374626685959813,
            "unit": "iter/sec",
            "range": "stddev: 0.01639991672791192",
            "extra": "mean: 1.0667091431999949 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6607532419602786,
            "unit": "iter/sec",
            "range": "stddev: 0.034755156657523295",
            "extra": "mean: 1.5134242807999954 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6022470389302543,
            "unit": "iter/sec",
            "range": "stddev: 0.005978707488448386",
            "extra": "mean: 624.1234814000052 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.687233546212525,
            "unit": "iter/sec",
            "range": "stddev: 0.030578633988746017",
            "extra": "mean: 175.832413400002 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.42752401831248,
            "unit": "iter/sec",
            "range": "stddev: 0.00005021290035612384",
            "extra": "mean: 23.569605418604723 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.055469499275645,
            "unit": "iter/sec",
            "range": "stddev: 0.00314962679471325",
            "extra": "mean: 327.281944799995 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.711206323176599,
            "unit": "iter/sec",
            "range": "stddev: 0.00005712809887815626",
            "extra": "mean: 114.79466366666695 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "f1f9450e0b0d41485457d6a3211705c302f76ea4",
          "message": "fix(packaging): align macOS wheel support and verify artifact metadata (#36)\n\nCorrect the published macOS wheel minimum to 15+, document validated macOS 14 source-install smoke evidence, and guard README deployment targets and actual wheel metadata against drift. Preserve Python and Rust solver behavior.",
          "timestamp": "2026-10-19T16:06:27+08:00",
          "tree_id": "7b7d000fa66eb669406fb82a546024eb29f42206",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/f1f9450e0b0d41485457d6a3211705c302f76ea4"
        },
        "date": 1792397403867,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.47488407002338734,
            "unit": "iter/sec",
            "range": "stddev: 0.007286779411339788",
            "extra": "mean: 2.105777100400002 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 179.4606418087024,
            "unit": "iter/sec",
            "range": "stddev: 0.00016174977050957903",
            "extra": "mean: 5.572252444443827 msec\nrounds: 144"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.907995869581617,
            "unit": "iter/sec",
            "range": "stddev: 0.0007032916207870819",
            "extra": "mean: 100.92858466666144 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1540.8215966204016,
            "unit": "iter/sec",
            "range": "stddev: 0.00002809911024458911",
            "extra": "mean: 649.0044027117573 usec\nrounds: 1254"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 98.13841147707734,
            "unit": "iter/sec",
            "range": "stddev: 0.00013052652849446507",
            "extra": "mean: 10.189690101449978 msec\nrounds: 69"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5064.621415164763,
            "unit": "iter/sec",
            "range": "stddev: 0.000025135024104306732",
            "extra": "mean: 197.4481245539392 usec\nrounds: 3083"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.031981494477527,
            "unit": "iter/sec",
            "range": "stddev: 0.0004360577629581716",
            "extra": "mean: 62.37532149999462 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1680.9047119418647,
            "unit": "iter/sec",
            "range": "stddev: 0.000028395535734521",
            "extra": "mean: 594.9177207343004 usec\nrounds: 1307"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.255201768748698,
            "unit": "iter/sec",
            "range": "stddev: 0.0006076673635395743",
            "extra": "mean: 49.37003400000082 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3385.765592486622,
            "unit": "iter/sec",
            "range": "stddev: 0.00004778328722329145",
            "extra": "mean: 295.3541740217065 usec\nrounds: 2402"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 19.98487886109062,
            "unit": "iter/sec",
            "range": "stddev: 0.0007824627132512718",
            "extra": "mean: 50.03783145000398 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3625.866068308091,
            "unit": "iter/sec",
            "range": "stddev: 0.000014797613800481242",
            "extra": "mean: 275.79617701285423 usec\nrounds: 2497"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.395106011741197,
            "unit": "iter/sec",
            "range": "stddev: 0.023025162245367013",
            "extra": "mean: 156.36957357142072 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 730.6374660926482,
            "unit": "iter/sec",
            "range": "stddev: 0.000026710804156825138",
            "extra": "mean: 1.3686678365234493 msec\nrounds: 679"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.802659976881929,
            "unit": "iter/sec",
            "range": "stddev: 0.0007291979567714193",
            "extra": "mean: 147.0013205714216 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 729.5132677926225,
            "unit": "iter/sec",
            "range": "stddev: 0.000028320013492766844",
            "extra": "mean: 1.3707769880948462 msec\nrounds: 672"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.486822567347034,
            "unit": "iter/sec",
            "range": "stddev: 0.0058576051535890435",
            "extra": "mean: 222.8748708000012 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 40.772500174142095,
            "unit": "iter/sec",
            "range": "stddev: 0.00008060318251533234",
            "extra": "mean: 24.526335047616225 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.5336234559202975,
            "unit": "iter/sec",
            "range": "stddev: 0.023919793892933628",
            "extra": "mean: 394.69164120000073 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.36153841100797,
            "unit": "iter/sec",
            "range": "stddev: 0.00015893849686941282",
            "extra": "mean: 186.51363160000187 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.3669805386124783,
            "unit": "iter/sec",
            "range": "stddev: 0.021482235606367375",
            "extra": "mean: 731.5393099999994 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 17.585978564856237,
            "unit": "iter/sec",
            "range": "stddev: 0.000121820727742537",
            "extra": "mean: 56.86348338888555 msec\nrounds: 18"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.026845788523336,
            "unit": "iter/sec",
            "range": "stddev: 0.022803553079171583",
            "extra": "mean: 973.8560659999962 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.230466927451342,
            "unit": "iter/sec",
            "range": "stddev: 0.00008043016150697584",
            "extra": "mean: 309.55277439999804 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.44568111978175606,
            "unit": "iter/sec",
            "range": "stddev: 0.04391395182369822",
            "extra": "mean: 2.243756703200006 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.9417552564394035,
            "unit": "iter/sec",
            "range": "stddev: 0.004489431885337896",
            "extra": "mean: 1.0618470066000043 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6499153303955779,
            "unit": "iter/sec",
            "range": "stddev: 0.019951381930349905",
            "extra": "mean: 1.5386619660000007 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.5821322609499278,
            "unit": "iter/sec",
            "range": "stddev: 0.004701486838576506",
            "extra": "mean: 632.0584091999933 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.163392866317667,
            "unit": "iter/sec",
            "range": "stddev: 0.0023718321829921574",
            "extra": "mean: 162.2482975999958 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.400601396725406,
            "unit": "iter/sec",
            "range": "stddev: 0.00009517079364287029",
            "extra": "mean: 23.58457113953176 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.085660591058777,
            "unit": "iter/sec",
            "range": "stddev: 0.00063573305907424",
            "extra": "mean: 324.07971339999904 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.37933360152341,
            "unit": "iter/sec",
            "range": "stddev: 0.005320260836009892",
            "extra": "mean: 119.3412325555572 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "253f5f7221962611e102db826d4b64a3d87ca5f7",
          "message": "test(solver): tolerate disappearing Linux procfs tasks (#40)\n\nTreat ESRCH while reading a recently vanished /proc task as process exit, preserving strict lifecycle assertions and regression coverage.",
          "timestamp": "2026-10-19T17:02:53+08:00",
          "tree_id": "82a58353a9419a83586e601312e21d2d189fde2b",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/253f5f7221962611e102db826d4b64a3d87ca5f7"
        },
        "date": 1792400793448,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.47676003093219477,
            "unit": "iter/sec",
            "range": "stddev: 0.008706479702284355",
            "extra": "mean: 2.0974912641999994 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 177.55791811053643,
            "unit": "iter/sec",
            "range": "stddev: 0.0002394611587170654",
            "extra": "mean: 5.631965111110746 msec\nrounds: 153"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 9.979278958642302,
            "unit": "iter/sec",
            "range": "stddev: 0.0006471218001277109",
            "extra": "mean: 100.20764066666112 msec\nrounds: 9"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1528.4166618935153,
            "unit": "iter/sec",
            "range": "stddev: 0.000018731716320426224",
            "extra": "mean: 654.2718519969065 usec\nrounds: 1277"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 96.49735438249726,
            "unit": "iter/sec",
            "range": "stddev: 0.00017080768278907523",
            "extra": "mean: 10.3629784090887 msec\nrounds: 66"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5151.309801845607,
            "unit": "iter/sec",
            "range": "stddev: 0.000012957933561998558",
            "extra": "mean: 194.12538528389825 usec\nrounds: 3221"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 15.862261196978803,
            "unit": "iter/sec",
            "range": "stddev: 0.001030009765362935",
            "extra": "mean: 63.042714250000145 msec\nrounds: 12"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1697.248341980069,
            "unit": "iter/sec",
            "range": "stddev: 0.000016613432846082315",
            "extra": "mean: 589.188968559171 usec\nrounds: 1304"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 20.30509649297975,
            "unit": "iter/sec",
            "range": "stddev: 0.0005199975254147998",
            "extra": "mean: 49.248719421044775 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3408.4001203551493,
            "unit": "iter/sec",
            "range": "stddev: 0.000050086087410754336",
            "extra": "mean: 293.39278391288224 usec\nrounds: 2300"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 20.413062916187627,
            "unit": "iter/sec",
            "range": "stddev: 0.00028348155368734915",
            "extra": "mean: 48.98823876190558 msec\nrounds: 21"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3671.5660997101554,
            "unit": "iter/sec",
            "range": "stddev: 0.000015164084396301043",
            "extra": "mean: 272.3633383800289 usec\nrounds: 2444"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 6.439386443153621,
            "unit": "iter/sec",
            "range": "stddev: 0.01953080790946812",
            "extra": "mean: 155.29429842857212 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 723.7119015927573,
            "unit": "iter/sec",
            "range": "stddev: 0.00002127581146275548",
            "extra": "mean: 1.381765309923995 msec\nrounds: 655"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 6.788189389095401,
            "unit": "iter/sec",
            "range": "stddev: 0.0011709989319874765",
            "extra": "mean: 147.31468771428322 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 717.7866367920826,
            "unit": "iter/sec",
            "range": "stddev: 0.00005272767052805521",
            "extra": "mean: 1.3931716595744656 msec\nrounds: 658"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.446598044524383,
            "unit": "iter/sec",
            "range": "stddev: 0.0012923242364689803",
            "extra": "mean: 224.89102680000883 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 40.77827088421366,
            "unit": "iter/sec",
            "range": "stddev: 0.00005711458313687225",
            "extra": "mean: 24.522864219510744 msec\nrounds: 41"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.5670821421171666,
            "unit": "iter/sec",
            "range": "stddev: 0.0023461462170150243",
            "extra": "mean: 389.54733219999866 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.36218141750642,
            "unit": "iter/sec",
            "range": "stddev: 0.00016536364024692212",
            "extra": "mean: 186.49126579999802 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.3579642282857676,
            "unit": "iter/sec",
            "range": "stddev: 0.03154221576598413",
            "extra": "mean: 736.3964227999986 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 17.574696509669348,
            "unit": "iter/sec",
            "range": "stddev: 0.00011523259432676246",
            "extra": "mean: 56.89998683333246 msec\nrounds: 18"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0293833565409067,
            "unit": "iter/sec",
            "range": "stddev: 0.02519017168033386",
            "extra": "mean: 971.4553802000012 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.228311129512999,
            "unit": "iter/sec",
            "range": "stddev: 0.0002803354284247096",
            "extra": "mean: 309.7594872000002 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.44650069771610174,
            "unit": "iter/sec",
            "range": "stddev: 0.03241232606251416",
            "extra": "mean: 2.2396381575999897 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 0.934725974583576,
            "unit": "iter/sec",
            "range": "stddev: 0.0056935106819702395",
            "extra": "mean: 1.0698322580000024 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6520661082012369,
            "unit": "iter/sec",
            "range": "stddev: 0.035970420579927095",
            "extra": "mean: 1.5335868364000078 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.5907327969345915,
            "unit": "iter/sec",
            "range": "stddev: 0.008146648915805991",
            "extra": "mean: 628.6410903999979 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.554324575285603,
            "unit": "iter/sec",
            "range": "stddev: 0.02823451623280831",
            "extra": "mean: 180.03989260000708 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.376298185086924,
            "unit": "iter/sec",
            "range": "stddev: 0.00004493366877754354",
            "extra": "mean: 23.598097116277142 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.060561559670077,
            "unit": "iter/sec",
            "range": "stddev: 0.0018116887074357817",
            "extra": "mean: 326.7374239999924 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.713952467569987,
            "unit": "iter/sec",
            "range": "stddev: 0.00006029586973799376",
            "extra": "mean: 114.75848688888529 msec\nrounds: 9"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9937736da184cc2600368198c43ee07236a5f47f",
          "message": "Merge pull request #45 from PhysicsQoo/dev\n\nrelease: stage QuPRS v0.13.3 from dev to main\n\nMerge only the independently reviewed and fully validated v0.13.3 release candidate. Release-Ready 35/35 PASS, independent archive build/install 20/20 PASS, CodSpeed, Docker and Benchmark success. Publication remains a separate tag-gated operation.",
          "timestamp": "2026-10-20T10:08:04+08:00",
          "tree_id": "3c2f5074408b655ea98c832a51bfc91f7ffba3ee",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/9937736da184cc2600368198c43ee07236a5f47f"
        },
        "date": 1792462280369,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 0.6998843122726609,
            "unit": "iter/sec",
            "range": "stddev: 0.04901317066239079",
            "extra": "mean: 1.4288075649999996 sec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 238.2764969134996,
            "unit": "iter/sec",
            "range": "stddev: 0.000030496255893522505",
            "extra": "mean: 4.196805026737595 msec\nrounds: 187"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 15.23307820091305,
            "unit": "iter/sec",
            "range": "stddev: 0.0005331445949569384",
            "extra": "mean: 65.64661369230424 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2105.566088388086,
            "unit": "iter/sec",
            "range": "stddev: 0.000028466318982438206",
            "extra": "mean: 474.9316611408522 usec\nrounds: 1508"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 149.24578344844696,
            "unit": "iter/sec",
            "range": "stddev: 0.0001636785497079968",
            "extra": "mean: 6.700356799999135 msec\nrounds: 95"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 8273.625355429258,
            "unit": "iter/sec",
            "range": "stddev: 0.00000639009883003781",
            "extra": "mean: 120.86599973296921 usec\nrounds: 3745"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 23.536539059467025,
            "unit": "iter/sec",
            "range": "stddev: 0.0006117840370863292",
            "extra": "mean: 42.487130222222426 msec\nrounds: 18"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2294.1903975131304,
            "unit": "iter/sec",
            "range": "stddev: 0.0000143215400107791",
            "extra": "mean: 435.8836132711503 usec\nrounds: 1492"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 30.06218534823136,
            "unit": "iter/sec",
            "range": "stddev: 0.0005520785410274755",
            "extra": "mean: 33.264381428572115 msec\nrounds: 28"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 5417.734099013475,
            "unit": "iter/sec",
            "range": "stddev: 0.00003780529762617466",
            "extra": "mean: 184.57901065725832 usec\nrounds: 2815"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 30.397774341639792,
            "unit": "iter/sec",
            "range": "stddev: 0.00033122066236308275",
            "extra": "mean: 32.89714532258271 msec\nrounds: 31"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 5389.200111567229,
            "unit": "iter/sec",
            "range": "stddev: 0.000008052385488529014",
            "extra": "mean: 185.5562939393599 usec\nrounds: 2640"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 10.299396784634283,
            "unit": "iter/sec",
            "range": "stddev: 0.0007011401275010996",
            "extra": "mean: 97.09306485714819 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 910.2194616524571,
            "unit": "iter/sec",
            "range": "stddev: 0.000021530016759410404",
            "extra": "mean: 1.098636144501405 msec\nrounds: 782"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 10.145891341103122,
            "unit": "iter/sec",
            "range": "stddev: 0.0009823970981401463",
            "extra": "mean: 98.56206481817833 msec\nrounds: 11"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 904.2606769564325,
            "unit": "iter/sec",
            "range": "stddev: 0.000028507526804623694",
            "extra": "mean: 1.1058758005112062 msec\nrounds: 782"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 5.811965751031262,
            "unit": "iter/sec",
            "range": "stddev: 0.025995398518643603",
            "extra": "mean: 172.05882533333275 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 41.95281621298885,
            "unit": "iter/sec",
            "range": "stddev: 0.000053760243621020045",
            "extra": "mean: 23.836302071430282 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 3.2998393566924733,
            "unit": "iter/sec",
            "range": "stddev: 0.0009756834876279913",
            "extra": "mean: 303.04505519999907 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 6.439505021831111,
            "unit": "iter/sec",
            "range": "stddev: 0.00008936020291931695",
            "extra": "mean: 155.29143880000333 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.9059193663257967,
            "unit": "iter/sec",
            "range": "stddev: 0.010150394871070284",
            "extra": "mean: 524.6811683999965 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 19.218334432495123,
            "unit": "iter/sec",
            "range": "stddev: 0.00008409784361975637",
            "extra": "mean: 52.03364545000113 msec\nrounds: 20"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.3255014226076478,
            "unit": "iter/sec",
            "range": "stddev: 0.028728530186202868",
            "extra": "mean: 754.4314800000052 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.9356290465224673,
            "unit": "iter/sec",
            "range": "stddev: 0.00019428377425527796",
            "extra": "mean: 254.08898759998806 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5486221630222917,
            "unit": "iter/sec",
            "range": "stddev: 0.0425084156145042",
            "extra": "mean: 1.8227480904000004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1036339467314071,
            "unit": "iter/sec",
            "range": "stddev: 0.011575891073479156",
            "extra": "mean: 906.0975361999908 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.8549468883934982,
            "unit": "iter/sec",
            "range": "stddev: 0.03540230858267017",
            "extra": "mean: 1.1696633014000042 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.9595154137663353,
            "unit": "iter/sec",
            "range": "stddev: 0.00912980141160764",
            "extra": "mean: 510.3302546000009 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 8.41234555993505,
            "unit": "iter/sec",
            "range": "stddev: 0.0013345035286405306",
            "extra": "mean: 118.87291040000036 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 76.10875623950994,
            "unit": "iter/sec",
            "range": "stddev: 0.0016190188181182854",
            "extra": "mean: 13.139092653847301 msec\nrounds: 78"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.827220887656246,
            "unit": "iter/sec",
            "range": "stddev: 0.0013419558703349536",
            "extra": "mean: 261.28619940000135 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 10.059553195067844,
            "unit": "iter/sec",
            "range": "stddev: 0.005296605074054243",
            "extra": "mean: 99.40799363636704 msec\nrounds: 11"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "01318e636d5d39473b8263622e052297e7feb30d",
          "message": "release: promote QuPRS v0.14.0 from dev to main\n\nrelease: v0.14.0 dev → main Release-Ready acceptance",
          "timestamp": "2026-11-04T11:21:12+08:00",
          "tree_id": "9ebef260ebe3b39da366fcda459119d6a7c2866b",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/01318e636d5d39473b8263622e052297e7feb30d"
        },
        "date": 1793762720097,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.141603635710422,
            "unit": "iter/sec",
            "range": "stddev: 0.0206810529909574",
            "extra": "mean: 875.9607701999812 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 216.2675915118759,
            "unit": "iter/sec",
            "range": "stddev: 0.00005746748295338334",
            "extra": "mean: 4.623901311376499 msec\nrounds: 167"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 17.582030523813327,
            "unit": "iter/sec",
            "range": "stddev: 0.0004065476139722202",
            "extra": "mean: 56.876252071430955 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1787.0348948377853,
            "unit": "iter/sec",
            "range": "stddev: 0.000017198039082873843",
            "extra": "mean: 559.5861630283235 usec\nrounds: 1466"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 116.38855738954884,
            "unit": "iter/sec",
            "range": "stddev: 0.00022769580803171094",
            "extra": "mean: 8.591909913042668 msec\nrounds: 92"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5031.856845089382,
            "unit": "iter/sec",
            "range": "stddev: 0.00001278995908513669",
            "extra": "mean: 198.73379366424263 usec\nrounds: 3441"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 16.629240916855867,
            "unit": "iter/sec",
            "range": "stddev: 0.014554537323713363",
            "extra": "mean: 60.13503592857156 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1867.6573337442812,
            "unit": "iter/sec",
            "range": "stddev: 0.00007324570971110889",
            "extra": "mean: 535.4301251799756 usec\nrounds: 1390"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 87.38763363643181,
            "unit": "iter/sec",
            "range": "stddev: 0.0011463050862993947",
            "extra": "mean: 11.44326672307443 msec\nrounds: 65"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3389.5869249946218,
            "unit": "iter/sec",
            "range": "stddev: 0.00001573920134747659",
            "extra": "mean: 295.02119937566926 usec\nrounds: 2563"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 89.81974308053924,
            "unit": "iter/sec",
            "range": "stddev: 0.00010993925358090885",
            "extra": "mean: 11.133409712643285 msec\nrounds: 87"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3410.830153010383,
            "unit": "iter/sec",
            "range": "stddev: 0.000015934432314680636",
            "extra": "mean: 293.1837573669286 usec\nrounds: 2749"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 9.869620427952903,
            "unit": "iter/sec",
            "range": "stddev: 0.001436422843967766",
            "extra": "mean: 101.32101911110819 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 541.7773415237875,
            "unit": "iter/sec",
            "range": "stddev: 0.00002471841025579316",
            "extra": "mean: 1.8457767118636388 msec\nrounds: 531"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 9.427894960138437,
            "unit": "iter/sec",
            "range": "stddev: 0.015393177128216116",
            "extra": "mean: 106.06821609999315 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 536.4027754535242,
            "unit": "iter/sec",
            "range": "stddev: 0.000034315515101972516",
            "extra": "mean: 1.864270741616704 msec\nrounds: 507"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.215214926862574,
            "unit": "iter/sec",
            "range": "stddev: 0.0015571780650974866",
            "extra": "mean: 237.23582719999285 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.663669409614194,
            "unit": "iter/sec",
            "range": "stddev: 0.00015853861468944264",
            "extra": "mean: 23.439146558140436 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.3956963679780765,
            "unit": "iter/sec",
            "range": "stddev: 0.010248694954478218",
            "extra": "mean: 417.41516719999936 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.70867226267584,
            "unit": "iter/sec",
            "range": "stddev: 0.00006520036798216968",
            "extra": "mean: 175.17208100001653 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4670816249924408,
            "unit": "iter/sec",
            "range": "stddev: 0.032865344745645605",
            "extra": "mean: 681.625332200008 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 25.751371792908838,
            "unit": "iter/sec",
            "range": "stddev: 0.0002622587378866775",
            "extra": "mean: 38.83288269230653 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0865130071296458,
            "unit": "iter/sec",
            "range": "stddev: 0.02270403506393663",
            "extra": "mean: 920.3755439999782 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.420794110465142,
            "unit": "iter/sec",
            "range": "stddev: 0.0045922382918086",
            "extra": "mean: 292.3297830000138 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4557649741801262,
            "unit": "iter/sec",
            "range": "stddev: 0.024024081805381393",
            "extra": "mean: 2.1941133186000004 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.002018327440278,
            "unit": "iter/sec",
            "range": "stddev: 0.004747560488459389",
            "extra": "mean: 997.9857379999885 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6357582936599266,
            "unit": "iter/sec",
            "range": "stddev: 0.025869651288031037",
            "extra": "mean: 1.5729248205999966 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.643843384026125,
            "unit": "iter/sec",
            "range": "stddev: 0.005509327547368127",
            "extra": "mean: 608.330458800026 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.238193420298335,
            "unit": "iter/sec",
            "range": "stddev: 0.008884352021280613",
            "extra": "mean: 190.90551259999984 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 43.127543802329555,
            "unit": "iter/sec",
            "range": "stddev: 0.00015377282615372658",
            "extra": "mean: 23.187038069763307 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.944419788821935,
            "unit": "iter/sec",
            "range": "stddev: 0.0005348251207399393",
            "extra": "mean: 339.6254853999949 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.4930992167495,
            "unit": "iter/sec",
            "range": "stddev: 0.005189310495648035",
            "extra": "mean: 117.74264900001047 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 42.875765796457095,
            "unit": "iter/sec",
            "range": "stddev: 0.00023874101830115638",
            "extra": "mean: 23.32319858139145 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.5459792669386285,
            "unit": "iter/sec",
            "range": "stddev: 0.011259978929211649",
            "extra": "mean: 180.31080750000683 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 41.74877258608497,
            "unit": "iter/sec",
            "range": "stddev: 0.00010024725109050149",
            "extra": "mean: 23.952800000000575 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.013886121869751,
            "unit": "iter/sec",
            "range": "stddev: 0.008315715063440173",
            "extra": "mean: 986.3040615999921 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.6465185685540173,
            "unit": "iter/sec",
            "range": "stddev: 0.0056502340018410105",
            "extra": "mean: 607.3420726000109 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 26.17173995209245,
            "unit": "iter/sec",
            "range": "stddev: 0.00009753690120957011",
            "extra": "mean: 38.20915238461435 msec\nrounds: 26"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.0910749846946048,
            "unit": "iter/sec",
            "range": "stddev: 0.021619102114549656",
            "extra": "mean: 916.5272909999885 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "976eb5338144c5fff4d937210a013762fa2a7f99",
          "message": "release: promote QuPRS v0.14.1 from dev to main (#154)\n\nQuPRS v0.14.1 maintenance release promotion.\n\nRelease-Ready Main run 42002991672 PASS: exact source/installed artifact 35/35 jobs successful. Preserve distinct Rust CLI resource supervision and Python PyO3 API contracts; Python opt-in isolated worker is deferred to QOO-175.",
          "timestamp": "2026-11-05T18:19:41+08:00",
          "tree_id": "7cbfa20497ef03e4da12e817bc043ff40e877d6f",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/976eb5338144c5fff4d937210a013762fa2a7f99"
        },
        "date": 1793874215370,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.5766461188148453,
            "unit": "iter/sec",
            "range": "stddev: 0.03733634184912853",
            "extra": "mean: 634.257737400003 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 275.5224611355663,
            "unit": "iter/sec",
            "range": "stddev: 0.000031012870418830105",
            "extra": "mean: 3.6294681597953877 msec\nrounds: 194"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 26.40044969469941,
            "unit": "iter/sec",
            "range": "stddev: 0.0004926511995379006",
            "extra": "mean: 37.8781426666674 msec\nrounds: 18"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2553.5455538815263,
            "unit": "iter/sec",
            "range": "stddev: 0.000012851381406741159",
            "extra": "mean: 391.612359716844 usec\nrounds: 1693"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 163.67128451455093,
            "unit": "iter/sec",
            "range": "stddev: 0.004838388476160093",
            "extra": "mean: 6.109807245455427 msec\nrounds: 110"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 8180.983696605028,
            "unit": "iter/sec",
            "range": "stddev: 0.000007572093546946421",
            "extra": "mean: 122.23468926053272 usec\nrounds: 3408"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 26.232653362846506,
            "unit": "iter/sec",
            "range": "stddev: 0.00033069050892930535",
            "extra": "mean: 38.120428999999945 msec\nrounds: 20"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2724.0620093705943,
            "unit": "iter/sec",
            "range": "stddev: 0.0000652896989245356",
            "extra": "mean: 367.0988386314503 usec\nrounds: 1667"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 136.6423093583297,
            "unit": "iter/sec",
            "range": "stddev: 0.00010868438216237066",
            "extra": "mean: 7.318377482757613 msec\nrounds: 87"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 5160.70402917795,
            "unit": "iter/sec",
            "range": "stddev: 0.000009160252376026687",
            "extra": "mean: 193.7720114050583 usec\nrounds: 2718"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 136.67533370513954,
            "unit": "iter/sec",
            "range": "stddev: 0.0001157537540345213",
            "extra": "mean: 7.316609170732875 msec\nrounds: 123"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 5129.295230261493,
            "unit": "iter/sec",
            "range": "stddev: 0.000010293564951050612",
            "extra": "mean: 194.95855767869685 usec\nrounds: 2826"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 13.742446210734846,
            "unit": "iter/sec",
            "range": "stddev: 0.014567703564459049",
            "extra": "mean: 72.76724861537787 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 673.5520582661943,
            "unit": "iter/sec",
            "range": "stddev: 0.000021958363691227818",
            "extra": "mean: 1.484666237341955 msec\nrounds: 632"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 14.379563768573453,
            "unit": "iter/sec",
            "range": "stddev: 0.0030894977480360624",
            "extra": "mean: 69.5431388666672 msec\nrounds: 15"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 671.0067315180152,
            "unit": "iter/sec",
            "range": "stddev: 0.00001726246479624598",
            "extra": "mean: 1.4902980149509157 msec\nrounds: 602"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 5.746533420953593,
            "unit": "iter/sec",
            "range": "stddev: 0.0020974837191580914",
            "extra": "mean: 174.01795599999446 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 43.229912030586334,
            "unit": "iter/sec",
            "range": "stddev: 0.00019738723104970415",
            "extra": "mean: 23.13213127272785 msec\nrounds: 44"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 3.0196336252191,
            "unit": "iter/sec",
            "range": "stddev: 0.029492529224993957",
            "extra": "mean: 331.1660036000035 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 6.468893889668989,
            "unit": "iter/sec",
            "range": "stddev: 0.00004610215778815362",
            "extra": "mean: 154.58593339999425 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.9962473528168032,
            "unit": "iter/sec",
            "range": "stddev: 0.026154555302860902",
            "extra": "mean: 500.9399254000015 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 26.894859977679076,
            "unit": "iter/sec",
            "range": "stddev: 0.00021759437062398226",
            "extra": "mean: 37.18182585185171 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.4115902140678191,
            "unit": "iter/sec",
            "range": "stddev: 0.028688514314833664",
            "extra": "mean: 708.4208930000102 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 4.188508327463132,
            "unit": "iter/sec",
            "range": "stddev: 0.0000483578649569376",
            "extra": "mean: 238.74848080000675 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5657522674597862,
            "unit": "iter/sec",
            "range": "stddev: 0.018349981893143456",
            "extra": "mean: 1.7675580948000005 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1839014585587608,
            "unit": "iter/sec",
            "range": "stddev: 0.010537222415546596",
            "extra": "mean: 844.6648940000159 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.797663330909234,
            "unit": "iter/sec",
            "range": "stddev: 0.0058531976562829",
            "extra": "mean: 1.2536617408000041 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.9555461280501756,
            "unit": "iter/sec",
            "range": "stddev: 0.004660927947116744",
            "extra": "mean: 511.36610160000373 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 6.437721844538666,
            "unit": "iter/sec",
            "range": "stddev: 0.04156900848249201",
            "extra": "mean: 155.33445279999682 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.90754650883301,
            "unit": "iter/sec",
            "range": "stddev: 0.00017269278660783017",
            "extra": "mean: 23.30592358139468 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.6094948715502473,
            "unit": "iter/sec",
            "range": "stddev: 0.001702951630300981",
            "extra": "mean: 277.04707600000233 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 9.618027214602016,
            "unit": "iter/sec",
            "range": "stddev: 0.00004748133565030626",
            "extra": "mean: 103.97142550000353 msec\nrounds: 10"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 42.98307623041505,
            "unit": "iter/sec",
            "range": "stddev: 0.00010917309323259636",
            "extra": "mean: 23.26497048837083 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 6.916144619284726,
            "unit": "iter/sec",
            "range": "stddev: 0.033346305496801766",
            "extra": "mean: 144.58922637500038 msec\nrounds: 8"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.55140104600025,
            "unit": "iter/sec",
            "range": "stddev: 0.00015854326224263018",
            "extra": "mean: 23.50098881395112 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.1805061518485778,
            "unit": "iter/sec",
            "range": "stddev: 0.008675579049874723",
            "extra": "mean: 847.0942726000033 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.971447703494897,
            "unit": "iter/sec",
            "range": "stddev: 0.005650525921669696",
            "extra": "mean: 507.241454199999 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 26.72134381440337,
            "unit": "iter/sec",
            "range": "stddev: 0.00016883728183220552",
            "extra": "mean: 37.42326759258937 msec\nrounds: 27"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.3450826995824072,
            "unit": "iter/sec",
            "range": "stddev: 0.044801940954299464",
            "extra": "mean: 743.4487116000071 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "bc22a0ac21d0a42d4ff52d530808e0487e0d46b7",
          "message": "release: promote QuPRS v0.15.0 from dev to main (#174)\n\nPromote the protected dev v0.15.0 source after Release-Ready Main run 42360771065 passed all 35 jobs, including Release-Ready / Required, source correctness, built/installed wheel and sdist matrices, release builder parity and negative policy tests. Official signed tag and PyPI/docs publication remain separate.",
          "timestamp": "2026-11-07T18:41:09+08:00",
          "tree_id": "daa767b85697326a71717f34be543871df16c890",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/bc22a0ac21d0a42d4ff52d530808e0487e0d46b7"
        },
        "date": 1794048310910,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.365405700656894,
            "unit": "iter/sec",
            "range": "stddev: 0.024254477860335463",
            "extra": "mean: 732.3830562000012 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 227.71247080468495,
            "unit": "iter/sec",
            "range": "stddev: 0.000057287431881813084",
            "extra": "mean: 4.391503005813532 msec\nrounds: 172"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 20.390038549636454,
            "unit": "iter/sec",
            "range": "stddev: 0.013163700587115431",
            "extra": "mean: 49.043556124999554 msec\nrounds: 16"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2242.086601819157,
            "unit": "iter/sec",
            "range": "stddev: 0.000016632464036748594",
            "extra": "mean: 446.01310189741656 usec\nrounds: 1423"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 147.78267949395683,
            "unit": "iter/sec",
            "range": "stddev: 0.00032291378130835826",
            "extra": "mean: 6.76669284536076 msec\nrounds: 97"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 7746.709133848836,
            "unit": "iter/sec",
            "range": "stddev: 0.000008443924547315956",
            "extra": "mean: 129.08707203560192 usec\nrounds: 2943"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 21.922263755887023,
            "unit": "iter/sec",
            "range": "stddev: 0.00038428233704908255",
            "extra": "mean: 45.61572705881979 msec\nrounds: 17"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2286.5631943141398,
            "unit": "iter/sec",
            "range": "stddev: 0.000016510672288432412",
            "extra": "mean: 437.3375739129538 usec\nrounds: 1380"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 114.86419906509022,
            "unit": "iter/sec",
            "range": "stddev: 0.00013926238443097698",
            "extra": "mean: 8.705932815788225 msec\nrounds: 76"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 5011.435657962356,
            "unit": "iter/sec",
            "range": "stddev: 0.0000612067840126754",
            "extra": "mean: 199.54361748836635 usec\nrounds: 2413"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 114.39241574348218,
            "unit": "iter/sec",
            "range": "stddev: 0.00019946924571725795",
            "extra": "mean: 8.741838289720512 msec\nrounds: 107"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 4991.116544341547,
            "unit": "iter/sec",
            "range": "stddev: 0.000010781027484780782",
            "extra": "mean: 200.35597067628183 usec\nrounds: 2353"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 12.305831930952936,
            "unit": "iter/sec",
            "range": "stddev: 0.00031550144323793327",
            "extra": "mean: 81.26228325000066 msec\nrounds: 12"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 598.3752104519649,
            "unit": "iter/sec",
            "range": "stddev: 0.000025821047254182405",
            "extra": "mean: 1.6711922261028826 msec\nrounds: 544"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 11.661295340974704,
            "unit": "iter/sec",
            "range": "stddev: 0.014530652492110576",
            "extra": "mean: 85.75376669230431 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 594.9228695446569,
            "unit": "iter/sec",
            "range": "stddev: 0.000024587937274676678",
            "extra": "mean: 1.680890164409685 msec\nrounds: 517"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.448216694314121,
            "unit": "iter/sec",
            "range": "stddev: 0.027877580829718685",
            "extra": "mean: 224.80919179999432 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.63479461282326,
            "unit": "iter/sec",
            "range": "stddev: 0.00007987890864468233",
            "extra": "mean: 23.45502093023406 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.518477812305641,
            "unit": "iter/sec",
            "range": "stddev: 0.0012385246815300739",
            "extra": "mean: 397.06524120000495 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.124182713097761,
            "unit": "iter/sec",
            "range": "stddev: 0.00006831374610632087",
            "extra": "mean: 195.15307240000084 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.609156487642066,
            "unit": "iter/sec",
            "range": "stddev: 0.03126327631159287",
            "extra": "mean: 621.4435996000134 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 26.129472371748047,
            "unit": "iter/sec",
            "range": "stddev: 0.00022086196072489275",
            "extra": "mean: 38.270960307688014 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.1258172003649751,
            "unit": "iter/sec",
            "range": "stddev: 0.02587814856017987",
            "extra": "mean: 888.243668399997 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.224020853663218,
            "unit": "iter/sec",
            "range": "stddev: 0.0000740538467601236",
            "extra": "mean: 310.171691000005 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.47097561746031774,
            "unit": "iter/sec",
            "range": "stddev: 0.02931633364859068",
            "extra": "mean: 2.1232521661999955 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.0439415634426217,
            "unit": "iter/sec",
            "range": "stddev: 0.0003362674038106448",
            "extra": "mean: 957.908023799996 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6540574722736542,
            "unit": "iter/sec",
            "range": "stddev: 0.01118676455759248",
            "extra": "mean: 1.5289176294000129 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6026860690286748,
            "unit": "iter/sec",
            "range": "stddev: 0.00013493520697682604",
            "extra": "mean: 623.9525128000025 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.688994758198936,
            "unit": "iter/sec",
            "range": "stddev: 0.0015039652921415537",
            "extra": "mean: 175.77797879999935 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.93465654403332,
            "unit": "iter/sec",
            "range": "stddev: 0.00015866081037182084",
            "extra": "mean: 23.291207627908026 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.9420651075089137,
            "unit": "iter/sec",
            "range": "stddev: 0.0006448064190747313",
            "extra": "mean: 339.89730460000374 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.043082877097175,
            "unit": "iter/sec",
            "range": "stddev: 0.00004593751991411105",
            "extra": "mean: 124.33043588889505 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 43.22232135769899,
            "unit": "iter/sec",
            "range": "stddev: 0.00006131383712661265",
            "extra": "mean: 23.13619372092968 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.718771257030133,
            "unit": "iter/sec",
            "range": "stddev: 0.0006471186330498792",
            "extra": "mean: 174.86273800000163 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 40.59848852904147,
            "unit": "iter/sec",
            "range": "stddev: 0.003332451962788232",
            "extra": "mean: 24.63145886046142 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.0458694687231171,
            "unit": "iter/sec",
            "range": "stddev: 0.00046509309547526065",
            "extra": "mean: 956.1422623999931 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.6012907171799788,
            "unit": "iter/sec",
            "range": "stddev: 0.0046662356964306505",
            "extra": "mean: 624.4962200000089 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 26.23964810167364,
            "unit": "iter/sec",
            "range": "stddev: 0.00011130405218781805",
            "extra": "mean: 38.11026718518443 msec\nrounds: 27"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.1143868944770403,
            "unit": "iter/sec",
            "range": "stddev: 0.02504504641739711",
            "extra": "mean: 897.3544152000102 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "0b244c10edbb659d4a1e35f47178304823ff1212",
          "message": "release(rc): synchronize v0.15.0 cache and native crate publishing gates (#191)\n\nBring the exact validated dev source tree to main: PR #189 Ganak cache-first/retry reliability and PR #190 default-disabled optional crates.io publisher with native Rust README.\n\nRelease-Ready Main #42499933064: 36/36 jobs PASS including Release-Ready / Required. CodSpeed Performance Analysis: Performance Gate Passed. No algorithm/API changes, no Rust path rename, and no tag/registry publication in this merge.\n\nQOO-36 QOO-176",
          "timestamp": "2026-11-09T06:49:57+08:00",
          "tree_id": "97084a785e5eb8524e42d5d47cfa11b946f382f2",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/0b244c10edbb659d4a1e35f47178304823ff1212"
        },
        "date": 1794178405242,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.5626005045112006,
            "unit": "iter/sec",
            "range": "stddev: 0.018506178452948677",
            "extra": "mean: 639.9588359999996 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 258.11579376795635,
            "unit": "iter/sec",
            "range": "stddev: 0.00009702866391616497",
            "extra": "mean: 3.8742301871654954 msec\nrounds: 187"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 24.064791788721752,
            "unit": "iter/sec",
            "range": "stddev: 0.010275587085610806",
            "extra": "mean: 41.5544837777762 msec\nrounds: 18"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2536.521167893528,
            "unit": "iter/sec",
            "range": "stddev: 0.00001943764911395829",
            "extra": "mean: 394.24074699540444 usec\nrounds: 1664"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 170.3106357587583,
            "unit": "iter/sec",
            "range": "stddev: 0.0001477817888549137",
            "extra": "mean: 5.871623903844035 msec\nrounds: 104"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 8745.161249192697,
            "unit": "iter/sec",
            "range": "stddev: 0.0000075827214985204764",
            "extra": "mean: 114.34894926520815 usec\nrounds: 3607"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 25.098502275540554,
            "unit": "iter/sec",
            "range": "stddev: 0.0005037688426270953",
            "extra": "mean: 39.843014894738886 msec\nrounds: 19"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2576.970092142781,
            "unit": "iter/sec",
            "range": "stddev: 0.00007673022849404518",
            "extra": "mean: 388.0526215841675 usec\nrounds: 1464"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 129.88349308561527,
            "unit": "iter/sec",
            "range": "stddev: 0.00023081355353211127",
            "extra": "mean: 7.699207776471105 msec\nrounds: 85"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 4266.983137051435,
            "unit": "iter/sec",
            "range": "stddev: 0.00009432164649297009",
            "extra": "mean: 234.35761705189648 usec\nrounds: 2768"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 128.93532142989636,
            "unit": "iter/sec",
            "range": "stddev: 0.0002716244021704342",
            "extra": "mean: 7.75582663392755 msec\nrounds: 112"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 5609.958457039317,
            "unit": "iter/sec",
            "range": "stddev: 0.000011169324479976873",
            "extra": "mean: 178.25443943265043 usec\nrounds: 2749"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 12.972893541105222,
            "unit": "iter/sec",
            "range": "stddev: 0.01392999419414922",
            "extra": "mean: 77.08380530769432 msec\nrounds: 13"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 678.9707230493311,
            "unit": "iter/sec",
            "range": "stddev: 0.000045970326971087306",
            "extra": "mean: 1.4728175546493252 msec\nrounds: 613"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 13.162262863865696,
            "unit": "iter/sec",
            "range": "stddev: 0.013828855857385991",
            "extra": "mean: 75.97477807142842 msec\nrounds: 14"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 684.7388479945047,
            "unit": "iter/sec",
            "range": "stddev: 0.00013109359622055948",
            "extra": "mean: 1.460410787161919 msec\nrounds: 592"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 5.395504962946112,
            "unit": "iter/sec",
            "range": "stddev: 0.0033998707644473476",
            "extra": "mean: 185.33946440000477 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 43.803274064573856,
            "unit": "iter/sec",
            "range": "stddev: 0.00007263654011139811",
            "extra": "mean: 22.829343727270736 msec\nrounds: 44"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.8228228622575484,
            "unit": "iter/sec",
            "range": "stddev: 0.002240268455954546",
            "extra": "mean: 354.2553142000031 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.727484181198383,
            "unit": "iter/sec",
            "range": "stddev: 0.00008369198489714552",
            "extra": "mean: 174.59672840000167 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.8105777491422452,
            "unit": "iter/sec",
            "range": "stddev: 0.020256371573081786",
            "extra": "mean: 552.3098913999945 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 26.976715344894217,
            "unit": "iter/sec",
            "range": "stddev: 0.00018578949137826282",
            "extra": "mean: 37.069005148147745 msec\nrounds: 27"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.2508800942166798,
            "unit": "iter/sec",
            "range": "stddev: 0.021588555304255085",
            "extra": "mean: 799.4371360000059 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.663365233126526,
            "unit": "iter/sec",
            "range": "stddev: 0.005533701916374424",
            "extra": "mean: 272.9730551999978 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.5319167681709334,
            "unit": "iter/sec",
            "range": "stddev: 0.02647567644873717",
            "extra": "mean: 1.8799933746000022 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.1539965222560666,
            "unit": "iter/sec",
            "range": "stddev: 0.0003224187898125293",
            "extra": "mean: 866.5537380000046 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.7403034465657411,
            "unit": "iter/sec",
            "range": "stddev: 0.02228338517060017",
            "extra": "mean: 1.350797439400003 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.8021884956013563,
            "unit": "iter/sec",
            "range": "stddev: 0.0045333824407395185",
            "extra": "mean: 554.8809141999982 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 7.137843745742322,
            "unit": "iter/sec",
            "range": "stddev: 0.001755720748092457",
            "extra": "mean: 140.09833160000085 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 43.97376490007196,
            "unit": "iter/sec",
            "range": "stddev: 0.00010114991631494104",
            "extra": "mean: 22.740831999999244 msec\nrounds: 44"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 3.233836932463616,
            "unit": "iter/sec",
            "range": "stddev: 0.010496290444908157",
            "extra": "mean: 309.2301872000007 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.797072518027296,
            "unit": "iter/sec",
            "range": "stddev: 0.0001073441326911915",
            "extra": "mean: 113.67417944444152 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 47.03609920769756,
            "unit": "iter/sec",
            "range": "stddev: 0.003492921676329955",
            "extra": "mean: 21.260266409089212 msec\nrounds: 44"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 7.291627236812574,
            "unit": "iter/sec",
            "range": "stddev: 0.003026145354250597",
            "extra": "mean: 137.1435987500007 msec\nrounds: 8"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 43.81581553111921,
            "unit": "iter/sec",
            "range": "stddev: 0.00006741729410598598",
            "extra": "mean: 22.822809250001796 msec\nrounds: 44"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.162744348521448,
            "unit": "iter/sec",
            "range": "stddev: 0.015406719738448243",
            "extra": "mean: 860.0342811999951 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.8021555548711417,
            "unit": "iter/sec",
            "range": "stddev: 0.005528125465208212",
            "extra": "mean: 554.8910565999961 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 27.040963463196224,
            "unit": "iter/sec",
            "range": "stddev: 0.00025680602830730295",
            "extra": "mean: 36.980930851855106 msec\nrounds: 27"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.25508513021166,
            "unit": "iter/sec",
            "range": "stddev: 0.03014478580109474",
            "extra": "mean: 796.7587026000047 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cab508f8ce710133af048f3f757da88198862698",
          "message": "release: integrate unified Python and Rust publishing\n\nIntegrate verified dual-registry release safeguards, matching native crate artifacts, and public installation guidance.",
          "timestamp": "2026-11-09T20:06:20+08:00",
          "tree_id": "1622fd9ae0a111674e16399e456d3ec583241dc9",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/cab508f8ce710133af048f3f757da88198862698"
        },
        "date": 1794226222260,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.3123746017537494,
            "unit": "iter/sec",
            "range": "stddev: 0.03354354184574097",
            "extra": "mean: 761.9775624000056 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 222.82060688787794,
            "unit": "iter/sec",
            "range": "stddev: 0.00003998890226300885",
            "extra": "mean: 4.487915251497337 msec\nrounds: 167"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 19.180592284949558,
            "unit": "iter/sec",
            "range": "stddev: 0.01675749710104148",
            "extra": "mean: 52.136033400004564 msec\nrounds: 15"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 2168.778678585847,
            "unit": "iter/sec",
            "range": "stddev: 0.000018473231711014305",
            "extra": "mean: 461.08900362855394 usec\nrounds: 1378"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 145.3619863643483,
            "unit": "iter/sec",
            "range": "stddev: 0.00014246239643186088",
            "extra": "mean: 6.879377648937119 msec\nrounds: 94"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 7456.19678612415,
            "unit": "iter/sec",
            "range": "stddev: 0.000008732836116926175",
            "extra": "mean: 134.11663193506135 usec\nrounds: 2956"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 20.890902105526994,
            "unit": "iter/sec",
            "range": "stddev: 0.00040608017948745893",
            "extra": "mean: 47.86772705882507 msec\nrounds: 17"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 2223.214637642964,
            "unit": "iter/sec",
            "range": "stddev: 0.000014734495232346613",
            "extra": "mean: 449.7991255851898 usec\nrounds: 1282"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 111.03848843846077,
            "unit": "iter/sec",
            "range": "stddev: 0.00017578613820019035",
            "extra": "mean: 9.00588628378362 msec\nrounds: 74"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 4852.972213694469,
            "unit": "iter/sec",
            "range": "stddev: 0.00006494327317721044",
            "extra": "mean: 206.0592881982978 usec\nrounds: 2415"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 111.24696541082544,
            "unit": "iter/sec",
            "range": "stddev: 0.0001726323639331796",
            "extra": "mean: 8.989009240001167 msec\nrounds: 100"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 4876.848890146306,
            "unit": "iter/sec",
            "range": "stddev: 0.000010413115794835516",
            "extra": "mean: 205.050437798166 usec\nrounds: 2307"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 10.97527862391054,
            "unit": "iter/sec",
            "range": "stddev: 0.019095254453524686",
            "extra": "mean: 91.11386000000205 msec\nrounds: 11"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 576.4409523565375,
            "unit": "iter/sec",
            "range": "stddev: 0.00014107020593674113",
            "extra": "mean: 1.7347830613212307 msec\nrounds: 424"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 11.727792677894772,
            "unit": "iter/sec",
            "range": "stddev: 0.0009471436919309026",
            "extra": "mean: 85.26753733333454 msec\nrounds: 12"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 579.8136929603995,
            "unit": "iter/sec",
            "range": "stddev: 0.000030214917287618173",
            "extra": "mean: 1.7246919349114072 msec\nrounds: 507"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.575788633853431,
            "unit": "iter/sec",
            "range": "stddev: 0.0004507989348440337",
            "extra": "mean: 218.54156300000795 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.055631399494644,
            "unit": "iter/sec",
            "range": "stddev: 0.00019985939709784334",
            "extra": "mean: 23.778028452380255 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.285414670201772,
            "unit": "iter/sec",
            "range": "stddev: 0.03158122269605164",
            "extra": "mean: 437.5573557999928 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.110805999854547,
            "unit": "iter/sec",
            "range": "stddev: 0.00032820099647491523",
            "extra": "mean: 195.66385419999506 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.547854218859705,
            "unit": "iter/sec",
            "range": "stddev: 0.03517003392103234",
            "extra": "mean: 646.0556735999944 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 25.48106301592994,
            "unit": "iter/sec",
            "range": "stddev: 0.0005304489416387385",
            "extra": "mean: 39.244830538460356 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.086558685362734,
            "unit": "iter/sec",
            "range": "stddev: 0.0031217467921922054",
            "extra": "mean: 920.3368520000026 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.1182174444056883,
            "unit": "iter/sec",
            "range": "stddev: 0.00016790695439744148",
            "extra": "mean: 320.69604440000603 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.45410809474161445,
            "unit": "iter/sec",
            "range": "stddev: 0.01511335453686335",
            "extra": "mean: 2.202118860200005 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.0014543031261984,
            "unit": "iter/sec",
            "range": "stddev: 0.00026905111809577624",
            "extra": "mean: 998.5478088000036 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6361440990793858,
            "unit": "iter/sec",
            "range": "stddev: 0.009701887055454578",
            "extra": "mean: 1.5719708811999964 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.5406475737328946,
            "unit": "iter/sec",
            "range": "stddev: 0.005339634536298334",
            "extra": "mean: 649.0777106000053 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.18206841363219,
            "unit": "iter/sec",
            "range": "stddev: 0.02969532451763263",
            "extra": "mean: 192.9731373999914 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.61622706357224,
            "unit": "iter/sec",
            "range": "stddev: 0.0000935638073790128",
            "extra": "mean: 23.465240095240297 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.900120116652974,
            "unit": "iter/sec",
            "range": "stddev: 0.0012662034103018951",
            "extra": "mean: 344.8133041999995 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 7.396769790874702,
            "unit": "iter/sec",
            "range": "stddev: 0.0013520568541354615",
            "extra": "mean: 135.19414937499974 msec\nrounds: 8"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 42.87059929733932,
            "unit": "iter/sec",
            "range": "stddev: 0.00006898578940777278",
            "extra": "mean: 23.326009348837427 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.18829152164716,
            "unit": "iter/sec",
            "range": "stddev: 0.03117626447985626",
            "extra": "mean: 192.74167533333278 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.15558276831756,
            "unit": "iter/sec",
            "range": "stddev: 0.00005016738762007967",
            "extra": "mean: 23.7216504750009 msec\nrounds: 40"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.0060141665663471,
            "unit": "iter/sec",
            "range": "stddev: 0.011128738673187566",
            "extra": "mean: 994.0217873999984 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.556210143398172,
            "unit": "iter/sec",
            "range": "stddev: 0.00009223417480221545",
            "extra": "mean: 642.5867382000092 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 25.997401689689173,
            "unit": "iter/sec",
            "range": "stddev: 0.00011102721850271376",
            "extra": "mean: 38.465382499998455 msec\nrounds: 26"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.0643297640665685,
            "unit": "iter/sec",
            "range": "stddev: 0.0382350430885133",
            "extra": "mean: 939.5584280000037 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "fab96235e0e40775efcd201723e9e1fcb7a8b75e",
          "message": "release: integrate reviewed Rust packaging and documentation safeguards\n\nPromote the source-verified release implementation through the protected integration branch while preserving signed Git ancestry.",
          "timestamp": "2026-11-09T22:37:21+08:00",
          "tree_id": "f72a24413fb356ad5ff76be4b0e54086d5e9cdb8",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/fab96235e0e40775efcd201723e9e1fcb7a8b75e"
        },
        "date": 1794235303812,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.1225523482440731,
            "unit": "iter/sec",
            "range": "stddev: 0.028131662185886353",
            "extra": "mean: 890.8270528000116 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 212.98806016839535,
            "unit": "iter/sec",
            "range": "stddev: 0.00011136550398639109",
            "extra": "mean: 4.695098867088452 msec\nrounds: 158"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 15.757537003586037,
            "unit": "iter/sec",
            "range": "stddev: 0.018813715230357755",
            "extra": "mean: 63.46169453845636 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1773.17796741829,
            "unit": "iter/sec",
            "range": "stddev: 0.000018502439284361924",
            "extra": "mean: 563.9591842300968 usec\nrounds: 1357"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 115.51837880077724,
            "unit": "iter/sec",
            "range": "stddev: 0.00016927950869472492",
            "extra": "mean: 8.656631181819112 msec\nrounds: 77"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5001.941169854281,
            "unit": "iter/sec",
            "range": "stddev: 0.000012247199577125798",
            "extra": "mean: 199.92238333925317 usec\nrounds: 3013"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 17.23489905197681,
            "unit": "iter/sec",
            "range": "stddev: 0.0018220241661852223",
            "extra": "mean: 58.02180778571499 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1793.7705181253702,
            "unit": "iter/sec",
            "range": "stddev: 0.000024806938662926154",
            "extra": "mean: 557.4849123092278 usec\nrounds: 1243"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 89.43218081676378,
            "unit": "iter/sec",
            "range": "stddev: 0.00015783239069516427",
            "extra": "mean: 11.181657328125372 msec\nrounds: 64"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3466.573354065547,
            "unit": "iter/sec",
            "range": "stddev: 0.0000581130208020498",
            "extra": "mean: 288.4693032176038 usec\nrounds: 2424"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 89.57956508767654,
            "unit": "iter/sec",
            "range": "stddev: 0.0001318978461950882",
            "extra": "mean: 11.163260270590106 msec\nrounds: 85"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3491.673409133979,
            "unit": "iter/sec",
            "range": "stddev: 0.000013427277512476427",
            "extra": "mean: 286.3956283494523 usec\nrounds: 2314"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 9.141406107441577,
            "unit": "iter/sec",
            "range": "stddev: 0.022830425531482443",
            "extra": "mean: 109.39236133333452 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 542.3559326484752,
            "unit": "iter/sec",
            "range": "stddev: 0.000026185332429395508",
            "extra": "mean: 1.8438076174749691 msec\nrounds: 515"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 9.831001080379785,
            "unit": "iter/sec",
            "range": "stddev: 0.0008788049652359871",
            "extra": "mean: 101.71904080000047 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 540.019969106306,
            "unit": "iter/sec",
            "range": "stddev: 0.00002161933539976886",
            "extra": "mean: 1.851783373224008 msec\nrounds: 493"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 3.981309582910677,
            "unit": "iter/sec",
            "range": "stddev: 0.02923072035368408",
            "extra": "mean: 251.17363499999783 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 41.982926383503234,
            "unit": "iter/sec",
            "range": "stddev: 0.0001497932686708556",
            "extra": "mean: 23.8192066666639 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.2950065463753515,
            "unit": "iter/sec",
            "range": "stddev: 0.0288283291903094",
            "extra": "mean: 435.7286046000013 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.704077501620455,
            "unit": "iter/sec",
            "range": "stddev: 0.00009524926629351513",
            "extra": "mean: 175.31318599999963 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4645797241774736,
            "unit": "iter/sec",
            "range": "stddev: 0.029019515957532997",
            "extra": "mean: 682.78973379999 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 25.48377204422925,
            "unit": "iter/sec",
            "range": "stddev: 0.0001092890940441107",
            "extra": "mean: 39.24065865384508 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0659226342488068,
            "unit": "iter/sec",
            "range": "stddev: 0.03640776439176507",
            "extra": "mean: 938.1543912000097 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.4380957293762244,
            "unit": "iter/sec",
            "range": "stddev: 0.0001022118116875154",
            "extra": "mean: 290.8586841999977 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4417010568874237,
            "unit": "iter/sec",
            "range": "stddev: 0.021878247031747195",
            "extra": "mean: 2.2639746597999872 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.0128993038315959,
            "unit": "iter/sec",
            "range": "stddev: 0.008371842403133148",
            "extra": "mean: 987.2649691999982 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6135360910234843,
            "unit": "iter/sec",
            "range": "stddev: 0.026976321023148116",
            "extra": "mean: 1.6298959663999995 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6208617243216492,
            "unit": "iter/sec",
            "range": "stddev: 0.004267655732567134",
            "extra": "mean: 616.9557741999938 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.047918955734135,
            "unit": "iter/sec",
            "range": "stddev: 0.0021247319073194365",
            "extra": "mean: 198.10143719998905 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.01737233469559,
            "unit": "iter/sec",
            "range": "stddev: 0.00006455539757839124",
            "extra": "mean: 23.79967961904786 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.811852545820445,
            "unit": "iter/sec",
            "range": "stddev: 0.03239095549633518",
            "extra": "mean: 355.6374253999934 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.168998824460434,
            "unit": "iter/sec",
            "range": "stddev: 0.004358247830706276",
            "extra": "mean: 122.41402177776057 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 42.400139531560285,
            "unit": "iter/sec",
            "range": "stddev: 0.00008954667641042141",
            "extra": "mean: 23.584828046512822 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.071500859152858,
            "unit": "iter/sec",
            "range": "stddev: 0.0006980692776930838",
            "extra": "mean: 197.18028799999843 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 41.79238953461678,
            "unit": "iter/sec",
            "range": "stddev: 0.00010167620382425288",
            "extra": "mean: 23.927801476192133 msec\nrounds: 42"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.0023379597059776,
            "unit": "iter/sec",
            "range": "stddev: 0.012979199592714343",
            "extra": "mean: 997.6674935999995 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.5940664287218151,
            "unit": "iter/sec",
            "range": "stddev: 0.005597801983497904",
            "extra": "mean: 627.3264287999837 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 25.752229609715165,
            "unit": "iter/sec",
            "range": "stddev: 0.0004243540560307971",
            "extra": "mean: 38.831589153847275 msec\nrounds: 26"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.084451067993961,
            "unit": "iter/sec",
            "range": "stddev: 0.004032520888964322",
            "extra": "mean: 922.1255153999891 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "7ac1fcbffda09b8292c6edb79001d16b03c4889f",
          "message": "Merge v0.15.0 beta candidate from dev (#215)\n\nIntegrate the verified prerelease source, release packaging checks, and documentation CI changes while preserving development branch history.",
          "timestamp": "2026-11-10T09:54:23+08:00",
          "tree_id": "2201bcd584db1e68e3c190470c4d36c29230a875",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/7ac1fcbffda09b8292c6edb79001d16b03c4889f"
        },
        "date": 1794275906453,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.1114936837790863,
            "unit": "iter/sec",
            "range": "stddev: 0.031179934461570025",
            "extra": "mean: 899.690222800001 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 217.75532217843173,
            "unit": "iter/sec",
            "range": "stddev: 0.00003863521063555963",
            "extra": "mean: 4.5923102590373714 msec\nrounds: 166"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 17.523176388980687,
            "unit": "iter/sec",
            "range": "stddev: 0.0010700842779786048",
            "extra": "mean: 57.06727923077018 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1801.1892931679677,
            "unit": "iter/sec",
            "range": "stddev: 0.00003291085655415955",
            "extra": "mean: 555.1887321299696 usec\nrounds: 1385"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 106.26772191102772,
            "unit": "iter/sec",
            "range": "stddev: 0.006667214027123509",
            "extra": "mean: 9.410195137496657 msec\nrounds: 80"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5087.30354639599,
            "unit": "iter/sec",
            "range": "stddev: 0.000010069550896262384",
            "extra": "mean: 196.56778701723667 usec\nrounds: 3235"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 17.770397342504346,
            "unit": "iter/sec",
            "range": "stddev: 0.002213479700120494",
            "extra": "mean: 56.27336185714528 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1895.5357530287645,
            "unit": "iter/sec",
            "range": "stddev: 0.00008004419704353509",
            "extra": "mean: 527.555335425438 usec\nrounds: 1434"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 89.29962748660357,
            "unit": "iter/sec",
            "range": "stddev: 0.0005048577053571753",
            "extra": "mean: 11.198255000000046 msec\nrounds: 64"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3560.093767442474,
            "unit": "iter/sec",
            "range": "stddev: 0.000013717551294658908",
            "extra": "mean: 280.89147795632005 usec\nrounds: 2427"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 89.7974052518093,
            "unit": "iter/sec",
            "range": "stddev: 0.00015436188734625636",
            "extra": "mean: 11.136179238094982 msec\nrounds: 84"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3516.974181097023,
            "unit": "iter/sec",
            "range": "stddev: 0.000012007655126750758",
            "extra": "mean: 284.3353259102054 usec\nrounds: 2335"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 9.404225324917494,
            "unit": "iter/sec",
            "range": "stddev: 0.01927200289285009",
            "extra": "mean: 106.33518077777164 msec\nrounds: 9"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 547.2761023819759,
            "unit": "iter/sec",
            "range": "stddev: 0.000042989252259577516",
            "extra": "mean: 1.8272312561202273 msec\nrounds: 531"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 9.978221583463105,
            "unit": "iter/sec",
            "range": "stddev: 0.0005425601555261519",
            "extra": "mean: 100.21825949999936 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 546.4504378690186,
            "unit": "iter/sec",
            "range": "stddev: 0.00003479300790463717",
            "extra": "mean: 1.8299921286543004 msec\nrounds: 513"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.030914628935905,
            "unit": "iter/sec",
            "range": "stddev: 0.02742707443838513",
            "extra": "mean: 248.08265419999316 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.74930224589176,
            "unit": "iter/sec",
            "range": "stddev: 0.00009179184874466785",
            "extra": "mean: 23.392194666665016 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.3584577723498765,
            "unit": "iter/sec",
            "range": "stddev: 0.02370801149393238",
            "extra": "mean: 424.0058956000041 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.643258743914552,
            "unit": "iter/sec",
            "range": "stddev: 0.004464961623763631",
            "extra": "mean: 177.2025783999993 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.4775790227886259,
            "unit": "iter/sec",
            "range": "stddev: 0.02795730945726984",
            "extra": "mean: 676.7827538000006 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 25.893300724799246,
            "unit": "iter/sec",
            "range": "stddev: 0.00017284821755361192",
            "extra": "mean: 38.62002803845909 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0830278377866858,
            "unit": "iter/sec",
            "range": "stddev: 0.02850310195902042",
            "extra": "mean: 923.337300399993 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.4394829330651935,
            "unit": "iter/sec",
            "range": "stddev: 0.00008081521945643698",
            "extra": "mean: 290.74137580000183 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.45068670773107466,
            "unit": "iter/sec",
            "range": "stddev: 0.02676109495711101",
            "extra": "mean: 2.2188362400000075 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.019735318593845,
            "unit": "iter/sec",
            "range": "stddev: 0.008025261640707925",
            "extra": "mean: 980.6466264000164 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6354092166802515,
            "unit": "iter/sec",
            "range": "stddev: 0.00416971039593067",
            "extra": "mean: 1.5737889438000026 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6271141590131857,
            "unit": "iter/sec",
            "range": "stddev: 0.00014305879765631171",
            "extra": "mean: 614.5850273999713 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.471579815587144,
            "unit": "iter/sec",
            "range": "stddev: 0.01087302997249813",
            "extra": "mean: 182.76257200000146 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.69492885084851,
            "unit": "iter/sec",
            "range": "stddev: 0.001164323515893761",
            "extra": "mean: 23.4219853953481 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.9484252608102843,
            "unit": "iter/sec",
            "range": "stddev: 0.000328939222653849",
            "extra": "mean: 339.16410000000496 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.599712329112544,
            "unit": "iter/sec",
            "range": "stddev: 0.004433693033573071",
            "extra": "mean: 116.28295944443481 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 43.23740395981262,
            "unit": "iter/sec",
            "range": "stddev: 0.0001051842505455563",
            "extra": "mean: 23.128123069772155 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 4.821690048666051,
            "unit": "iter/sec",
            "range": "stddev: 0.02555039710373769",
            "extra": "mean: 207.3961598333464 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.569070995583495,
            "unit": "iter/sec",
            "range": "stddev: 0.00014643664708694659",
            "extra": "mean: 23.491233813952604 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.020514014519454,
            "unit": "iter/sec",
            "range": "stddev: 0.008435402370300094",
            "extra": "mean: 979.8983509999971 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.632935870787629,
            "unit": "iter/sec",
            "range": "stddev: 0.00032175559006517317",
            "extra": "mean: 612.3939205999932 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 26.122698681427078,
            "unit": "iter/sec",
            "range": "stddev: 0.00009520974485697409",
            "extra": "mean: 38.2808840769192 msec\nrounds: 26"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.081283066862106,
            "unit": "iter/sec",
            "range": "stddev: 0.030424624788064847",
            "extra": "mean: 924.8272081999858 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "80d68e7e3fa3d8f5d657d1a4e9c00538beaf7bb4",
          "message": "release: prepare v0.15.0-rc.2 candidate (#220)\n\nAlign native and Python prerelease versions, harden crate publication verification, and retain full release candidate acceptance tests.",
          "timestamp": "2026-11-10T13:23:54+08:00",
          "tree_id": "154446b76e7767d04f4f4bc095621194cfc12cb3",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/80d68e7e3fa3d8f5d657d1a4e9c00538beaf7bb4"
        },
        "date": 1794288482495,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.1324519001626963,
            "unit": "iter/sec",
            "range": "stddev: 0.019681640594357515",
            "extra": "mean: 883.0397121999908 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 217.6804347336066,
            "unit": "iter/sec",
            "range": "stddev: 0.00006306749142711669",
            "extra": "mean: 4.593890127166376 msec\nrounds: 173"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 16.785829510155217,
            "unit": "iter/sec",
            "range": "stddev: 0.011996138662198903",
            "extra": "mean: 59.57405914286288 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1791.8114523324803,
            "unit": "iter/sec",
            "range": "stddev: 0.00001715197892370841",
            "extra": "mean: 558.094434935247 usec\nrounds: 1414"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 117.12632058732804,
            "unit": "iter/sec",
            "range": "stddev: 0.00010601740271178005",
            "extra": "mean: 8.537790609194552 msec\nrounds: 87"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5024.228850739288,
            "unit": "iter/sec",
            "range": "stddev: 0.000011051974872239422",
            "extra": "mean: 199.03551962065887 usec\nrounds: 3797"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 18.190451590631636,
            "unit": "iter/sec",
            "range": "stddev: 0.00027772177784797937",
            "extra": "mean: 54.97389633333872 msec\nrounds: 15"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1875.933812563248,
            "unit": "iter/sec",
            "range": "stddev: 0.00007101324488469743",
            "extra": "mean: 533.06784775824 usec\nrounds: 1583"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 90.20096216414171,
            "unit": "iter/sec",
            "range": "stddev: 0.0001489538079539476",
            "extra": "mean: 11.086356242855443 msec\nrounds: 70"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3560.381413920125,
            "unit": "iter/sec",
            "range": "stddev: 0.000011938871053814755",
            "extra": "mean: 280.86878447636855 usec\nrounds: 2770"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 90.20377399305843,
            "unit": "iter/sec",
            "range": "stddev: 0.0002444316736847085",
            "extra": "mean: 11.086010659342858 msec\nrounds: 91"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3514.835905006845,
            "unit": "iter/sec",
            "range": "stddev: 0.000012612271877458207",
            "extra": "mean: 284.5083033821041 usec\nrounds: 2927"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 10.216700947205476,
            "unit": "iter/sec",
            "range": "stddev: 0.0003860650337996093",
            "extra": "mean: 97.87895380000577 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 540.304492576762,
            "unit": "iter/sec",
            "range": "stddev: 0.000017318059568850245",
            "extra": "mean: 1.8508082270997002 msec\nrounds: 524"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 9.239998955878638,
            "unit": "iter/sec",
            "range": "stddev: 0.01775471209659448",
            "extra": "mean: 108.22512045456278 msec\nrounds: 11"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 529.4520640048382,
            "unit": "iter/sec",
            "range": "stddev: 0.00015663862611542157",
            "extra": "mean: 1.8887451159145199 msec\nrounds: 509"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 4.149898565772627,
            "unit": "iter/sec",
            "range": "stddev: 0.024094163573125153",
            "extra": "mean: 240.96974519998184 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.823541017132,
            "unit": "iter/sec",
            "range": "stddev: 0.0001003936972628861",
            "extra": "mean: 23.35164202324931 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.5233656900277333,
            "unit": "iter/sec",
            "range": "stddev: 0.0018056029638298355",
            "extra": "mean: 396.2961071999871 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.719424764507554,
            "unit": "iter/sec",
            "range": "stddev: 0.00011467696486484167",
            "extra": "mean: 174.84275799999978 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.5046337069779763,
            "unit": "iter/sec",
            "range": "stddev: 0.02745235631580572",
            "extra": "mean: 664.6135836000099 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 26.106631360989546,
            "unit": "iter/sec",
            "range": "stddev: 0.00009283088736298653",
            "extra": "mean: 38.30444403847038 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0993762952439279,
            "unit": "iter/sec",
            "range": "stddev: 0.022896599082769434",
            "extra": "mean: 909.6066599999972 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.445895295010349,
            "unit": "iter/sec",
            "range": "stddev: 0.00038801437918797936",
            "extra": "mean: 290.2003440000044 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.4611983565576563,
            "unit": "iter/sec",
            "range": "stddev: 0.02889829519212081",
            "extra": "mean: 2.1682644480000137 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.0301030502297472,
            "unit": "iter/sec",
            "range": "stddev: 0.016655616883460136",
            "extra": "mean: 970.7766614000093 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6492752120031601,
            "unit": "iter/sec",
            "range": "stddev: 0.004578119478386149",
            "extra": "mean: 1.5401789280000002 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6551334868798204,
            "unit": "iter/sec",
            "range": "stddev: 0.0003901124717345638",
            "extra": "mean: 604.1808760000094 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.06161460946509,
            "unit": "iter/sec",
            "range": "stddev: 0.0019050182080806884",
            "extra": "mean: 197.56541680001192 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 43.32027738081974,
            "unit": "iter/sec",
            "range": "stddev: 0.00006333285365300959",
            "extra": "mean: 23.08387804651396 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.8966841551037947,
            "unit": "iter/sec",
            "range": "stddev: 0.02368282827360138",
            "extra": "mean: 345.2223115999914 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.681188818469762,
            "unit": "iter/sec",
            "range": "stddev: 0.003376932272873788",
            "extra": "mean: 115.19159655558218 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 43.4093110824093,
            "unit": "iter/sec",
            "range": "stddev: 0.0000755403933609769",
            "extra": "mean: 23.036532372088914 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.738473379580873,
            "unit": "iter/sec",
            "range": "stddev: 0.008225355809535269",
            "extra": "mean: 174.2623749999931 msec\nrounds: 6"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.91471879791757,
            "unit": "iter/sec",
            "range": "stddev: 0.00007672606541618765",
            "extra": "mean: 23.30202848838252 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.03585047673055,
            "unit": "iter/sec",
            "range": "stddev: 0.008337051040544633",
            "extra": "mean: 965.3902975999927 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.6580876069802297,
            "unit": "iter/sec",
            "range": "stddev: 0.0002349752234496606",
            "extra": "mean: 603.1044413999552 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 26.176895986177836,
            "unit": "iter/sec",
            "range": "stddev: 0.00010339222059273985",
            "extra": "mean: 38.20162637036986 msec\nrounds: 27"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.0962580323500286,
            "unit": "iter/sec",
            "range": "stddev: 0.02463898858583381",
            "extra": "mean: 912.1940003999953 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "b48e3efc86eb5ab4925272d5724c71fd09f04867",
          "message": "Merge pull request #227 from dev\n\nchore(release): promote v0.15.0 stable source to main",
          "timestamp": "2026-11-10T19:13:05+08:00",
          "tree_id": "62f24d0b980ca7b027deebfc4cb1b5db11d947c0",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/b48e3efc86eb5ab4925272d5724c71fd09f04867"
        },
        "date": 1794309431872,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.1125839678163079,
            "unit": "iter/sec",
            "range": "stddev: 0.029530859006817213",
            "extra": "mean: 898.808565399986 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 214.74789574874376,
            "unit": "iter/sec",
            "range": "stddev: 0.000060789156841586305",
            "extra": "mean: 4.6566230440274285 msec\nrounds: 159"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 17.007619616368725,
            "unit": "iter/sec",
            "range": "stddev: 0.001166915262960518",
            "extra": "mean: 58.797175769239644 msec\nrounds: 13"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 1783.1321835236613,
            "unit": "iter/sec",
            "range": "stddev: 0.000018708610978825663",
            "extra": "mean: 560.8109198185701 usec\nrounds: 1322"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 102.24318533082756,
            "unit": "iter/sec",
            "range": "stddev: 0.008192571042448927",
            "extra": "mean: 9.780602949373174 msec\nrounds: 79"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 5014.563409717377,
            "unit": "iter/sec",
            "range": "stddev: 0.000013554628158073496",
            "extra": "mean: 199.41915542680525 usec\nrounds: 2921"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 17.175557666068407,
            "unit": "iter/sec",
            "range": "stddev: 0.0006715171891915633",
            "extra": "mean: 58.222272571421335 msec\nrounds: 14"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 1861.7856921497385,
            "unit": "iter/sec",
            "range": "stddev: 0.00001905670106677284",
            "extra": "mean: 537.1187479936723 usec\nrounds: 1246"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 86.77810777512644,
            "unit": "iter/sec",
            "range": "stddev: 0.00024012678648815922",
            "extra": "mean: 11.523643758070444 msec\nrounds: 62"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 3474.6638842763723,
            "unit": "iter/sec",
            "range": "stddev: 0.00006533541089039605",
            "extra": "mean: 287.79762109515764 usec\nrounds: 2209"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 88.00442773093269,
            "unit": "iter/sec",
            "range": "stddev: 0.0002333593497262768",
            "extra": "mean: 11.363064629627832 msec\nrounds: 81"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 3451.0408954491722,
            "unit": "iter/sec",
            "range": "stddev: 0.00002135311699554153",
            "extra": "mean: 289.76764700722117 usec\nrounds: 2272"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 8.606826459866186,
            "unit": "iter/sec",
            "range": "stddev: 0.026047432590228882",
            "extra": "mean: 116.18684362500176 msec\nrounds: 8"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 547.8371880979573,
            "unit": "iter/sec",
            "range": "stddev: 0.0000313157694812047",
            "extra": "mean: 1.8253598363263952 msec\nrounds: 501"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 9.56093583047955,
            "unit": "iter/sec",
            "range": "stddev: 0.0013456303410057028",
            "extra": "mean: 104.5922719000032 msec\nrounds: 10"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 538.3110299227335,
            "unit": "iter/sec",
            "range": "stddev: 0.0001595480606395835",
            "extra": "mean: 1.8576621031590883 msec\nrounds: 475"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 3.8931384571492473,
            "unit": "iter/sec",
            "range": "stddev: 0.029604215527872187",
            "extra": "mean: 256.8621719999783 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 41.47587296032378,
            "unit": "iter/sec",
            "range": "stddev: 0.0005862397665354555",
            "extra": "mean: 24.110402714286682 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 2.279388673191262,
            "unit": "iter/sec",
            "range": "stddev: 0.029299526315434362",
            "extra": "mean: 438.71412180001244 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 5.637191000532365,
            "unit": "iter/sec",
            "range": "stddev: 0.004359409668861054",
            "extra": "mean: 177.39331519999268 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 1.441435674036599,
            "unit": "iter/sec",
            "range": "stddev: 0.039871214389440274",
            "extra": "mean: 693.752775799976 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 25.28553970448373,
            "unit": "iter/sec",
            "range": "stddev: 0.000627809594963937",
            "extra": "mean: 39.54829565384662 msec\nrounds: 26"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.0649749291706567,
            "unit": "iter/sec",
            "range": "stddev: 0.03432942072307341",
            "extra": "mean: 938.9892406000058 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 3.3819229787075145,
            "unit": "iter/sec",
            "range": "stddev: 0.008517277604675804",
            "extra": "mean: 295.68976180000845 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.44416851160667153,
            "unit": "iter/sec",
            "range": "stddev: 0.023638304887325528",
            "extra": "mean: 2.251397777800014 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.0173518812511593,
            "unit": "iter/sec",
            "range": "stddev: 0.005504189850570138",
            "extra": "mean: 982.9440712000064 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.6244672024752748,
            "unit": "iter/sec",
            "range": "stddev: 0.025031772801669017",
            "extra": "mean: 1.601365125399991 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 1.6224365609823266,
            "unit": "iter/sec",
            "range": "stddev: 0.004291120286258305",
            "extra": "mean: 616.3569189999862 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 5.096182930853639,
            "unit": "iter/sec",
            "range": "stddev: 0.0015357409934625766",
            "extra": "mean: 196.22529520000853 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 42.515772350448096,
            "unit": "iter/sec",
            "range": "stddev: 0.00017449056161812277",
            "extra": "mean: 23.520682906974418 msec\nrounds: 43"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 2.942921541699394,
            "unit": "iter/sec",
            "range": "stddev: 0.0012486789368858268",
            "extra": "mean: 339.79838939999354 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 8.178717600235025,
            "unit": "iter/sec",
            "range": "stddev: 0.004348292048110709",
            "extra": "mean: 122.26855711111284 msec\nrounds: 9"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 42.59240187327812,
            "unit": "iter/sec",
            "range": "stddev: 0.00015091992992838352",
            "extra": "mean: 23.47836600000213 msec\nrounds: 42"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 5.00794325905709,
            "unit": "iter/sec",
            "range": "stddev: 0.0248604938130977",
            "extra": "mean: 199.6827736000114 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.26144316093606,
            "unit": "iter/sec",
            "range": "stddev: 0.00013380540310800856",
            "extra": "mean: 23.662230279072435 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.0106085283124244,
            "unit": "iter/sec",
            "range": "stddev: 0.011140731540181165",
            "extra": "mean: 989.5028311999909 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 1.6144224108353824,
            "unit": "iter/sec",
            "range": "stddev: 0.005337642336758476",
            "extra": "mean: 619.4165747999932 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 25.593578352271482,
            "unit": "iter/sec",
            "range": "stddev: 0.001453899368461865",
            "extra": "mean: 39.07230111537912 msec\nrounds: 26"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.067584718238157,
            "unit": "iter/sec",
            "range": "stddev: 0.048884395682083234",
            "extra": "mean: 936.6938126000036 msec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "34832121+PhysicsQoo@users.noreply.github.com",
            "name": "Wei-Jia Huang",
            "username": "PhysicsQoo"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "f0f5e0f5c9023606cad1abda44c8fd7d42788eaf",
          "message": "chore(release): promote v0.15.1-rc.1 for publication\n\nPromote the reviewed, full Release-Ready-passing QuPRS maintenance candidate, including pinned GPMC v1.0.2 distribution, removed git submodule, source/installed-artifact verification, and synchronized release metadata.",
          "timestamp": "2026-11-12T13:26:22+08:00",
          "tree_id": "eb01f59517914c209ff86ea516ff8b65997e89bd",
          "url": "https://github.com/PhysicsQoo/QuPRS/commit/f0f5e0f5c9023606cad1abda44c8fd7d42788eaf"
        },
        "date": 1794461371431,
        "tool": "pytest",
        "benches": [
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-python]",
            "value": 1.9733150554684453,
            "unit": "iter/sec",
            "range": "stddev: 0.06831916591887137",
            "extra": "mean: 506.76145059999556 msec\nrounds: 5"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[adder_8.qasm-proportional-False-rust]",
            "value": 361.52479590113273,
            "unit": "iter/sec",
            "range": "stddev: 0.0003060587990270297",
            "extra": "mean: 2.766062000000335 msec\nrounds: 234"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-python]",
            "value": 30.088906450040845,
            "unit": "iter/sec",
            "range": "stddev: 0.01700505441828779",
            "extra": "mean: 33.23484027777428 msec\nrounds: 18"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[gf2^4_mult.qasm-proportional-False-rust]",
            "value": 3709.1878852632253,
            "unit": "iter/sec",
            "range": "stddev: 0.000011196652737668816",
            "extra": "mean: 269.60079427980617 usec\nrounds: 1993"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-python]",
            "value": 251.95936294768956,
            "unit": "iter/sec",
            "range": "stddev: 0.00024755160542019476",
            "extra": "mean: 3.9688939847320324 msec\nrounds: 131"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[tof_3.qasm-proportional-True-rust]",
            "value": 11680.31012579362,
            "unit": "iter/sec",
            "range": "stddev: 0.00003791134413112986",
            "extra": "mean: 85.61416514033311 usec\nrounds: 3603"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-python]",
            "value": 33.62159388765227,
            "unit": "iter/sec",
            "range": "stddev: 0.0012865999065038575",
            "extra": "mean: 29.742789807691302 msec\nrounds: 26"
          },
          {
            "name": "test/test_Feynman.py::test_all_benchmarks[vbe_adder_3.qasm-proportional-True-rust]",
            "value": 3921.4876593356744,
            "unit": "iter/sec",
            "range": "stddev: 0.00001247660963935253",
            "extra": "mean: 255.00526506040475 usec\nrounds: 1577"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-python]",
            "value": 182.55173823987846,
            "unit": "iter/sec",
            "range": "stddev: 0.00015507703517619452",
            "extra": "mean: 5.47789908571547 msec\nrounds: 105"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-gpmc-rust]",
            "value": 7824.991684423117,
            "unit": "iter/sec",
            "range": "stddev: 0.000008288244601141209",
            "extra": "mean: 127.7956629641739 usec\nrounds: 2881"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-python]",
            "value": 181.25638782162957,
            "unit": "iter/sec",
            "range": "stddev: 0.00031650002063302073",
            "extra": "mean: 5.517046941176373 msec\nrounds: 153"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[ghz_nativegates_ibm_qiskit_opt0_32.qasm-straightforward-True-ganak-rust]",
            "value": 7822.846412576293,
            "unit": "iter/sec",
            "range": "stddev: 0.000007625459212764643",
            "extra": "mean: 127.8307085758917 usec\nrounds: 2927"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-python]",
            "value": 17.035419779811555,
            "unit": "iter/sec",
            "range": "stddev: 0.02044734856778315",
            "extra": "mean: 58.70122444444171 msec\nrounds: 18"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-gpmc-rust]",
            "value": 961.7994687128767,
            "unit": "iter/sec",
            "range": "stddev: 0.000021874822068315263",
            "extra": "mean: 1.0397177712504302 msec\nrounds: 800"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-python]",
            "value": 17.932818068475722,
            "unit": "iter/sec",
            "range": "stddev: 0.021823955438268774",
            "extra": "mean: 55.76368400000164 msec\nrounds: 19"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[graphstate_nativegates_ibm_qiskit_opt0_16.qasm-naive-False-ganak-rust]",
            "value": 944.5987275261834,
            "unit": "iter/sec",
            "range": "stddev: 0.00009629133143446522",
            "extra": "mean: 1.058650589778908 msec\nrounds: 724"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-python]",
            "value": 6.337598042483148,
            "unit": "iter/sec",
            "range": "stddev: 0.03465709304464182",
            "extra": "mean: 157.7884860000032 msec\nrounds: 7"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-gpmc-rust]",
            "value": 42.835893893427034,
            "unit": "iter/sec",
            "range": "stddev: 0.0002247783278175835",
            "extra": "mean: 23.344907952380687 msec\nrounds: 42"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-python]",
            "value": 3.383385775609931,
            "unit": "iter/sec",
            "range": "stddev: 0.04435308410168221",
            "extra": "mean: 295.5619211999931 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm-proportional-True-ganak-rust]",
            "value": 7.94712815059251,
            "unit": "iter/sec",
            "range": "stddev: 0.004541767227377714",
            "extra": "mean: 125.8316187999867 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-python]",
            "value": 2.3834839518971935,
            "unit": "iter/sec",
            "range": "stddev: 0.04826956418796374",
            "extra": "mean: 419.5539052000015 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-gpmc-rust]",
            "value": 38.62453607574096,
            "unit": "iter/sec",
            "range": "stddev: 0.0004754750721888673",
            "extra": "mean: 25.890278605263905 msec\nrounds: 38"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-python]",
            "value": 1.6365092750369374,
            "unit": "iter/sec",
            "range": "stddev: 0.07354450637927061",
            "extra": "mean: 611.0567261999961 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qaoa_nativegates_ibm_qiskit_opt0_7.qasm-proportional-False-ganak-rust]",
            "value": 5.114070649934919,
            "unit": "iter/sec",
            "range": "stddev: 0.004264438214041658",
            "extra": "mean: 195.5389489999959 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-python]",
            "value": 0.6877062321129037,
            "unit": "iter/sec",
            "range": "stddev: 0.032980655542229155",
            "extra": "mean: 1.4541092595999998 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-gpmc-rust]",
            "value": 1.6122989106900298,
            "unit": "iter/sec",
            "range": "stddev: 0.011137332840628093",
            "extra": "mean: 620.2323857999886 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-python]",
            "value": 0.9366503639280098,
            "unit": "iter/sec",
            "range": "stddev: 0.034311596106406855",
            "extra": "mean: 1.0676342406000061 sec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[qft_nativegates_ibm_qiskit_opt0_16.qasm-proportional-True-ganak-rust]",
            "value": 2.437090487612522,
            "unit": "iter/sec",
            "range": "stddev: 0.00006523127313682185",
            "extra": "mean: 410.325346999997 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-python]",
            "value": 7.967538495311578,
            "unit": "iter/sec",
            "range": "stddev: 0.03842061330323717",
            "extra": "mean: 125.50927750000085 msec\nrounds: 6"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-gpmc-rust]",
            "value": 75.83074948479735,
            "unit": "iter/sec",
            "range": "stddev: 0.0030988030457499817",
            "extra": "mean: 13.187262512821153 msec\nrounds: 78"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-python]",
            "value": 4.317908791313503,
            "unit": "iter/sec",
            "range": "stddev: 0.002589804635313302",
            "extra": "mean: 231.59359039999572 msec\nrounds: 5"
          },
          {
            "name": "test/test_MQT.py::test_all_benchmarks[vqe_nativegates_ibm_qiskit_opt0_4.qasm-proportional-False-ganak-rust]",
            "value": 11.99644285075579,
            "unit": "iter/sec",
            "range": "stddev: 0.00005173164512228144",
            "extra": "mean: 83.35804308332939 msec\nrounds: 12"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-rust]",
            "value": 72.99773023664909,
            "unit": "iter/sec",
            "range": "stddev: 0.003664647667766226",
            "extra": "mean: 13.699056076923638 msec\nrounds: 78"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[vqe4-gpmc-python]",
            "value": 8.294865184065921,
            "unit": "iter/sec",
            "range": "stddev: 0.03511828755588697",
            "extra": "mean: 120.55651030000547 msec\nrounds: 10"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[grover4-gpmc-rust]",
            "value": 42.76390969159848,
            "unit": "iter/sec",
            "range": "stddev: 0.0002674808741787602",
            "extra": "mean: 23.384204279069063 msec\nrounds: 43"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-gpmc-rust]",
            "value": 1.5849986521884647,
            "unit": "iter/sec",
            "range": "stddev: 0.012334954024216404",
            "extra": "mean: 630.9153630000026 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qft16-ganak-rust]",
            "value": 2.49805340562301,
            "unit": "iter/sec",
            "range": "stddev: 0.004666273387324304",
            "extra": "mean: 400.3116977999923 msec\nrounds: 5"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-gpmc-rust]",
            "value": 38.72406633303929,
            "unit": "iter/sec",
            "range": "stddev: 0.0002748501714267124",
            "extra": "mean: 25.823734300000467 msec\nrounds: 40"
          },
          {
            "name": "test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[qaoa7-ganak-python]",
            "value": 1.68468907561884,
            "unit": "iter/sec",
            "range": "stddev: 0.03928090415848991",
            "extra": "mean: 593.5813405999966 msec\nrounds: 5"
          }
        ]
      }
    ]
  }
}