window.BENCHMARK_DATA = {
  "lastUpdate": 1768374827261,
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
      }
    ]
  }
}