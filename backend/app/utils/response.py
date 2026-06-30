def success(data=None, message="Success"):
    return {
        "success": True,
        "message": message,
        "data": data
    }
 
 
def fail(message="Something went wrong", data=None):
    return {
        "success": False,
        "message": message,
        "data": data
    }
 