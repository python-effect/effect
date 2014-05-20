class DumbThing(object):
    pass

def schedule_DumbThing_QBANG(dumbthing, handlers):
    print("Doing dumb thing!")
    return "Dumb Thing Result"

def pure():
    dt = DumbThing()
    return Callback(dt, lambda x: print("got result:", x))

def main():
    p = pure()
    handlers = standard_handlers.copy()
    handlers[DumbThing] = schedule_DumbThing_QBANG
    schedule_iop_QBANG(p, handlers)

if __name__ == '__main__':
    main()
