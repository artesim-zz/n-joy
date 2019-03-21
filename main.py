import zmq

from njoy_core.input_node import EmbeddedInputNode
from njoy_core.core import Core


def main():
    ctx = zmq.Context()

    core = Core(context=ctx,
                input_events="inproc://input_events",
                output_events="inproc://output_events",
                requests="inproc://requests")

    input_node = EmbeddedInputNode(context=ctx,
                                   events_endpoint="inproc://input_events",
                                   requests_endpoint="inproc://requests")

    core.start()
    input_node.start()

    core.join()
    input_node.join()


if __name__ == "__main__":
    main()
