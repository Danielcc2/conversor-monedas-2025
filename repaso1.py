alumnos = [
    {"nombre": "Ana", "nota": 4},
    {"nombre": "Luis", "nota": 7},
    {"nombre": "Pedro", "nota": 9},
    {"nombre": "Marta", "nota": 5},
    {"nombre": "Sofía", "nota": 10}
]



print(

    list(
        map(
        lambda x: f"{x['nombre']} - {x['nota']}",
        sorted(
            filter(
                lambda x: x["nota"] >= 5, alumnos
            ), 
                key=lambda x: x["nota"], reverse=True
        )






        )
    )
    




)










