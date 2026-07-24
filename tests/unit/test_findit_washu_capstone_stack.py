import aws_cdk as core
import aws_cdk.assertions as assertions

from findit_washu_capstone.findit_washu_capstone_stack import FinditWashuCapstoneStack

# example tests. To run these tests, uncomment this file along with the example
# resource in findit_washu_capstone/findit_washu_capstone_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = FinditWashuCapstoneStack(app, "findit-washu-capstone")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
