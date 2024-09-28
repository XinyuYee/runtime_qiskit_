import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
# from qiskit_aer import AerSimulator
from qiskit.circuit.random import random_circuit
import random
import pickle
import json
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Options
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# pip install qiskit-ibm-runtime
# pip install qiskit

# def expectation_value_fast(state_counts):
#     total_counts = sum(state_counts.values())
#     expectation = 0
#     for state, count in state_counts.items():
#         state = state.split(' ')[-1]
#         state_int = int(state, 2)
#         num_ones = bin(state_int).count('1')
#         outcome = (-1) ** num_ones
#         probability = count / total_counts
#         expectation += outcome * probability
#     return expectation

def expectation_value_fast(state_counts):
    expectation_value = 0
    total_shots = sum(state_counts.values())
    for bitstring, count in state_counts.items():
        z_contribution = (-1) ** bitstring.count('1')
        expectation_value += z_contribution * count / total_shots
    return expectation_value

if __name__ == "__main__":
    # simulator = AerSimulator(method='matrix_product_state') 

    test_num = 2
    train_num = 2
    num_qubits = 50

    #### load train data
    # circuits = []
    # init_qubit = 5
    # for i in range(test_num): 
    #     circ = QuantumCircuit(num_qubits)
    #     inits = random_circuit(num_qubits = init_qubit, depth=1, max_operands=1)
    #     act_qubit = random.sample(range(0, num_qubits), init_qubit)
    #     print(act_qubit)
    #     circ.compose(inits, qubits=act_qubit, inplace=True)
    #     circ.measure_all()
    #     circuits.append(circ)
    # print(circuits)

    #### load train data
    circuits = []
    init_qubit = 5
    inverse_data_cir = pickle.load(open('inversed_circ_dict.pkl', 'rb'))
    init_data = pickle.load(open('train_init_data.pkl', 'rb'))
    for i in range(train_num):  #init_data.keys():
        print('This is the results for circ, ', i)
        circ = QuantumCircuit(num_qubits)
        # init circuit
        inits = init_data[i]['circ']  # random_circuit(num_qubits = init_qubit, depth=1, max_operands=1)
        act_qubit = init_data[i]['act_qubit'] # random.sample(range(0, num_qubits), init_qubit)
        print(act_qubit)
        circ.compose(inits, qubits=act_qubit, inplace=True)
        # load torr
        circ_inver = inverse_data_cir[i]['circ']
        # circ_inver.measure_all()
        circ.compose(circ_inver, qubits=range(num_qubits), inplace=True)
        circuits.append(circ)
        print(init_data[i]['gt'])
        # tcirc = transpile(circ, simulator)
        # result = simulator.run(tcirc).result()
        # counts = result.get_counts()
        # ideal_ev = expectation_value_fast(counts)
        # print(ideal_ev, init_data[i]['gt'])

    # #### load test data
    # circuits = []
    # inverse_data_cir = pickle.load(open('new_test_data.pkl', 'rb'))
    # for i in range(test_num):  #init_data.keys():
    #     print('This is the results for circ, ', i)
    #     circ = inverse_data_cir[i]['circ']
    #     # circ.measure_all()
    #     circ.remove_final_measurements()
    #     circuits.append(circ)
    #     print(inverse_data_cir[i]['gt'])

    # service = QiskitRuntimeService.save_account(channel="ibm_quantum", token="15ea93f9f4a982b62708546ab41827398c2968d0a3f8de673a1008e91aa1cc5313c8c24e2f8a7b0d4527a4293b8cf734bdd19adb78a15f3c22290bc4b425c012")
    service = QiskitRuntimeService(instance='ibm-q/open/main')
    for backend_item in service.backends():
        if backend_item.name == 'ibm_brisbane':
            backend = backend_item
    print('backend:', backend.name)
    # backend = service.least_busy(operational = True, simlulator = False)

    # pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    # isa_circuits = pm.run(circuits)
    # sampler = Sampler(backend)
    # job = sampler.run(isa_circuits)
    # result = job.result()
    
    # # for idx, pub_result in enumerate(result):
    # #     print(f" > Counts for pub {idx}: {pub_result.data.meas.get_counts()}")

    # save_dict = {}
    # for i in range(test_num):
    #     pub_result = result[i]
    #     # print(f" > Counts for pub {i}: {pub_result.data.meas.get_counts()}")
    #     state_counts = pub_result.data.meas.get_counts()
    #     nosiy_ev = expectation_value_fast(state_counts)
    #     print(f" > Counts for pub {i}: {nosiy_ev}")
    #     save_dict[i] = {
    #         'nosiy_ev': nosiy_ev
    #     }
    #     # json.dump(save_dict, open('save_ibm_real.json', 'w'), indent = 4)
    # with open('save_dict.pkl', 'wb') as f:
    #     pickle.dump(save_dict, f)

    pubs = []
    observable = SparsePauliOp("Z" * num_qubits)
    # Get ISA circuits
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    for qc in circuits:
        isa_circuit = pm.run(qc)
        isa_obs = observable.apply_layout(isa_circuit.layout)
        pubs.append((isa_circuit, isa_obs))
    
    estimator = Estimator(backend)
    job = estimator.run(pubs)
    job_result = job.result()

    save_dict = {}
    for i in range(test_num):
        pub_result = job_result[i]
        print(f">>> Expectation values for PUB {i}: {pub_result.data.evs}")
        print(f">>> Standard errors for PUB {i}: {pub_result.data.stds}")

        save_dict[i] = {
            'nosiy_ev': pub_result.data.evs,
            'std_ev': pub_result.data.stds
        }
    with open('save_dict.pkl', 'wb') as f:
        pickle.dump(save_dict, f)

