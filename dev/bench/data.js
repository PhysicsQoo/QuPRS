window.BENCHMARK_DATA = {
  "lastUpdate": 1768454567572,
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
      }
    ]
  }
}