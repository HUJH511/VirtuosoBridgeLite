; read_connectivity.il
;
; Procedures:
;   ReadSchematic(libName cellName) - read connectivity as structured data
;
; Returns a SKILL association list:
;   list(
;     list("lib" libName)
;     list("cell" cellName)
;     list("view" viewName)
;     list("instances" list(list(name lib cell) ...))
;     list("nets" list(list(netName conn1 conn2 ...) ...))
;     list("pins" list(list(name direction) ...))
;   )

procedure(ReadSchematic(libName cellName)
  let((cv instances nets pins)
    cv = dbOpenCellViewByType(libName cellName "schematic" "schematic" "r")
    unless(cv
      return(sprintf(nil "ERROR: cannot open %s/%s/schematic" libName cellName)))

    instances = mapcar(lambda((inst)
      list(inst~>name inst~>libName inst~>cellName))
      cv~>instances)

    nets = mapcar(lambda((net)
      cons(net~>name
        mapcar(lambda((it)
          sprintf(nil "%s.%s" it~>inst~>name it~>name))
          net~>instTerms)))
      cv~>nets)

    pins = mapcar(lambda((term)
      list(term~>name term~>direction))
      cv~>terminals)

    list(
      list("lib" cv~>libName)
      list("cell" cv~>cellName)
      list("view" cv~>viewName)
      list("instances" instances)
      list("nets" nets)
      list("pins" pins))
  ))
