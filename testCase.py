from informationRepo import *

dupset = DuplicatdSet()

for i in range(5,16):
    dupset.addTuple(i, i+1, i+2, i+3, i+4)
    
print(dupset.dTupleList)

dupset.checkExist(1, 3)