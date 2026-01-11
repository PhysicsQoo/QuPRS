window.BENCHMARK_DATA = {
  "lastUpdate": 1768146725852,
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
      }
    ]
  }
}