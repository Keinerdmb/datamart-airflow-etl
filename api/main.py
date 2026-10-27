"""
API REST de Productos - DataMart S.A.S. (Servicio Legado)
Expone el catálogo de productos para enriquecer el pipeline ETL.
"""

from fastapi import FastAPI, HTTPException, Path, Query
from typing import Optional, List, Dict

app = FastAPI(
    title="DataMart Products API",
    version="1.0.0",
    description="API REST del catalogo legado. Puedes probar consultando codigos de ejemplo como: 23843, 22197, 23084, 85123A."
)

# Catálogo base del sistema legado de DataMart
CATALOGO_PRODUCTOS = [
    {"codigo": "23843", "nombre": "PAPER CRAFT LITTLE BIRDIE", "categoria": "Papelería", "pais_proveedor": "Colombia", "activo": True},
    {"codigo": "22197", "nombre": "SMALL POPCORN HOLDER", "categoria": "Hogar", "pais_proveedor": "Perú", "activo": True},
    {"codigo": "23084", "nombre": "RABBIT NIGHT LIGHT", "categoria": "Hogar", "pais_proveedor": "México", "activo": True},
    {"codigo": "22423", "nombre": "REGENCY CAKESTAND 3 TIER", "categoria": "Hogar", "pais_proveedor": "Colombia", "activo": True},
    {"codigo": "85123A", "nombre": "WHITE HANGING HEART T-LIGHT HOLDER", "categoria": "Hogar", "pais_proveedor": "Colombia", "activo": True},
    {"codigo": "46000S", "nombre": "POLYESTER FILLER PAD 40X40CM", "categoria": "Hogar", "pais_proveedor": "México", "activo": True},
    {"codigo": "22313", "nombre": "OFFICE MUG WARMER PINK", "categoria": "Electrónica", "pais_proveedor": "Perú", "activo": True},
    {"codigo": "22086", "nombre": "PAPER CHAIN KIT 50S CHRISTMAS", "categoria": "Papelería", "pais_proveedor": "Colombia", "activo": True},
    {"codigo": "22588", "nombre": "CARD HOLDER GINGHAM HEART", "categoria": "Papelería", "pais_proveedor": "México", "activo": True},
    {"codigo": "23250", "nombre": "VINTAGE RED TRIM ENAMEL BOWL", "categoria": "Hogar", "pais_proveedor": "Colombia", "activo": True},
]

# Diccionario indexado por código para búsquedas instantáneas O(1)
INDICE_PRODUCTOS = {p["codigo"].upper(): p for p in CATALOGO_PRODUCTOS}


@app.get("/")
def inicio():
    """Ruta base para validar que el servicio esté arriba."""
    return {"servicio": "DataMart Products API", "estado": "activo"}


@app.get("/products")
def listar_productos(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    """Devuelve el catálogo de productos con paginación."""
    inicio_idx = (page - 1) * limit
    fin_idx = inicio_idx + limit
    items = CATALOGO_PRODUCTOS[inicio_idx:fin_idx]
    
    return {
        "page": page,
        "limit": limit,
        "total_registros": len(CATALOGO_PRODUCTOS),
        "data": items
    }


@app.get("/products/{codigo}", summary="Obtener producto por codigo")
def obtener_producto(
    codigo: str = Path(
        ...,
        description="Codigo unico del producto. Ejemplos validos: 23843, 22197, 23084, 22423, 85123A",
        example="23843"
    )
):
    """
    Consulta los datos de un producto especifico por su codigo.
    
    Codigos de prueba disponibles:
    - `23843` (PAPER CRAFT LITTLE BIRDIE - Papeleria)
    - `22197` (SMALL POPCORN HOLDER - Hogar)
    - `23084` (RABBIT NIGHT LIGHT - Hogar)
    - `85123A` (WHITE HANGING HEART T-LIGHT HOLDER - Hogar)
    - `22313` (OFFICE MUG WARMER PINK - Electronica)
    """
    codigo_limpio = codigo.strip().upper()
    producto = INDICE_PRODUCTOS.get(codigo_limpio)
    
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto '{codigo}' no encontrado en catálogo")
    return producto
