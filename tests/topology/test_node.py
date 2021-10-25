from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node, QuantumRouter, BSMNode


def test_Node_assign_cchannel():
    tl = Timeline()
    node = Node("node1", tl)
    cc = ClassicalChannel("cc", tl, 1e3)
    node.assign_cchannel(cc, "node2")
    assert "node2" in node.cchannels and node.cchannels["node2"] == cc


def test_Node_assign_qchannel():
    tl = Timeline()
    node = Node("node1", tl)
    qc = QuantumChannel("qc", tl, 2e-4, 1e3)
    node.assign_qchannel(qc, "node2")
    assert "node2" in node.qchannels and node.qchannels["node2"] == qc


def test_Node_send_message():
    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_message(self, src, msg):
            self.log.append((self.timeline.now(), src, msg))

    tl = Timeline()
    node1 = FakeNode("node1", tl)
    node2 = FakeNode("node2", tl)
    cc0 = ClassicalChannel("cc0", tl, 1e3)
    cc1 = ClassicalChannel("cc1", tl, 1e3)
    cc0.set_ends(node1, node2)
    cc1.set_ends(node2, node1)

    MSG_NUM = 10
    CC_DELAY = cc0.delay

    for i in range(MSG_NUM):
        node1.send_message("node2", str(i))
        tl.time += 1

    for i in range(MSG_NUM):
        node2.send_message("node1", str(i))
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.init()
    tl.run()

    expect_node1_log = [(CC_DELAY + MSG_NUM + i, "node2", str(i))
                        for i in range(MSG_NUM)]
    for actual, expect in zip(node1.log, expect_node1_log):
        assert actual == expect

    expect_node2_log = [(CC_DELAY + i, "node1", str(i))
                        for i in range(MSG_NUM)]

    for actual, expect in zip(node2.log, expect_node2_log):
        assert actual == expect


def test_Node_send_qubit():
    from sequence.components.photon import Photon
    from numpy import random

    random.seed(0)

    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_qubit(self, src, qubit):
            self.log.append((self.timeline.now(), src, qubit.name))

    tl = Timeline()
    node1 = FakeNode("node1", tl)
    node2 = FakeNode("node2", tl)
    qc0 = QuantumChannel("qc0", tl, 2e-4, 2e4)
    qc1 = QuantumChannel("qc1", tl, 2e-4, 2e4)
    qc0.set_ends(node1, node2)
    qc1.set_ends(node2, node1)
    tl.init()

    for i in range(1000):
        photon = Photon(str(i))
        node1.send_qubit("node2", photon)
        tl.time += 1

    for i in range(1000):
        photon = Photon(str(i))
        node2.send_qubit("node1", photon)
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.run()

    expect_rate_0 = 1 - qc0.loss
    expect_rate_1 = 1 - qc1.loss
    assert abs(len(node1.log) / 1000 - expect_rate_1) < 0.1
    assert abs(len(node2.log) / 1000 - expect_rate_0) < 0.1


def test_QuantumRouter_init():
    tl = Timeline()
    node1 = QuantumRouter("node1", tl)
    for i in range(2, 50):
        node = QuantumRouter("node%d" % i, tl)
        mid = BSMNode("mid%d" % i, tl, [node1.name, node.name])
        qc = QuantumChannel("qc_l_%d" % i, tl, 0, 1000)
        qc.set_ends(node1, mid)
        qc = QuantumChannel("qc_r_%d" % i, tl, 0, 1000)
        qc.set_ends(node, mid)

    node1.init()

    assert len(node1.map_to_middle_node) == 48
    for i in range(2, 50):
        node_name = "node%d" % i
        assert node1.map_to_middle_node[node_name] == "mid%d" % i


def test_Node_seed():
    from numpy.random._generator import Generator

    def rng_equal(rng1: Generator, rng2: Generator) -> bool:
        return all([rng1.random() == rng2.random() for _ in range(10)])

    tl = Timeline()
    n1, n2 = [Node(f"node{i}", tl, seed=0) for i in range(2)]
    assert rng_equal(n1.get_generator(), n2.get_generator())

    n10, n11 = [Node(f"node{i}", tl, seed=i) for i in range(10, 12)]
    assert not rng_equal(n10.get_generator(), n11.get_generator())

    SEED = 111
    n_seed1, n_seed2 = [Node(f"node{i}", tl) for i in range(20, 22)]

    assert not rng_equal(n_seed1.get_generator(), n_seed2.get_generator())
    n_seed1.set_seed(SEED)
    n_seed2.set_seed(SEED)
    assert rng_equal(n_seed1.get_generator(), n_seed2.get_generator())
