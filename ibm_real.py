import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
# from qiskit_aer import AerSimulator
from qiskit.circuit.random import random_circuit
import random
import pickle
import json
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session, Options

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
    total_shots = sum(counts.values())
    for bitstring, count in counts.items():
        z_contribution = (-1) ** bitstring.count('1')
        expectation_value += z_contribution * count / total_shots
    return expectation_value

if __name__ == "__main__":
    # simulator = AerSimulator(method='matrix_product_state') 

    test_num = 2

    #### load train data
    circuits = []
    num_qubits = 50
    init_qubit = 5
    inverse_data_cir = pickle.load(open('inversed_circ_dict_large.pkl', 'rb'))
    init_data = pickle.load(open('select_train_init_data.pickle', 'rb'))
    for i in range(test_num):  #init_data.keys():
        print('This is the results for circ, ', i)
        circ = QuantumCircuit(num_qubits)
        # init circuit
        inits = init_data[i]['circ']  # random_circuit(num_qubits = init_qubit, depth=1, max_operands=1)
        act_qubit = init_data[i]['act_qubit'] # random.sample(range(0, num_qubits), init_qubit)
        print(act_qubit)
        circ.compose(inits, qubits=act_qubit, inplace=True)
        # load torr
        circ_inver = inverse_data_cir[i]['circ']
        circ_inver.measure_all()
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
    # inverse_data_cir = pickle.load(open('select_test_data.pickle', 'rb'))
    # for i in range(test_num):  #init_data.keys():
    #     print('This is the results for circ, ', i)
    #     circ = inverse_data_cir[i]['circ']
    #     circuits.append(circ)
    #     print(inverse_data_cir[i]['gt'])

    service = QiskitRuntimeService.save_account(channel="ibm_quantum", token="15ea93f9f4a982b62708546ab41827398c2968d0a3f8de673a1008e91aa1cc5313c8c24e2f8a7b0d4527a4293b8cf734bdd19adb78a15f3c22290bc4b425c012")
    service = QiskitRuntimeService(instance='ibm-q/open/main')
    for backend_item in service.backends():
        if backend_item.name == 'ibm_brisbane':
            backend = backend_item
    # backend = service.least_busy(operational = True, simlulator = False)
    print('backend:', backend.name)
    options = Options(optimization_level=3, resilience_level=1)
    jobs = []
    
    with Session(service=service, backend=backend):
        sample = Sampler(options=options)
        start_idx = 0
        while start_idx < len(circuits):
            end_idx = start_idx + min(backend.max_circuits, len(circuits) - start_idx)
            jobs.append(sample.run(circuits[start_idx:end_idx]))#, shots=10000
            start_idx = end_idx

    results = [job.result() for job in jobs]
    print(len(results))

    save_dict = {}
    for i in range(test_num):
        result = results[i]
        state_counts = result.get_counts()
        nosiy_ev = expectation_value_fast(state_counts)
        save_dict[i] = {
            'nosiy_ev': nosiy_ev
        }
        json.dump(save_dict, open('save_ibm_real.json', 'w'), indent = 4)
