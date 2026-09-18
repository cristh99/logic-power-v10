# Fixed-basis bound v1 — cota dual para la base fija mínima

Extensión post-release del núcleo `logic_power_v10` (fuera del manifiesto).
El núcleo calcula la **base fija mínima** enumerando 2^|E| subconjuntos;
este paquete añade el **testigo dual**: pesos racionales `y_p` sobre las
parejas conflictivas que prueban una cota inferior sobre toda base
separadora, verificable en tiempo polinómico y sin enumeración.

## Qué certifica y qué no

- `tight = true`: el valor dual iguala el costo de la base declarada ⇒ la
  base es mínima. **Sólo entonces** el certificado prueba minimalidad.
- `tight = false`: prueba una **cota inferior válida** y difiere la
  minimalidad al replay del núcleo. Hay brecha (`gap_triangle`: 2 vs 1).
- `obstruction != null`: lenguaje insuficiente; demás campos son `null`.

## El teorema dual en tres líneas

Para cada `e`: `Σ_{p separada por e} y_p ≤ cost(e)`. Para toda base `B`:
`cost(B) = Σ_{e∈B} cost(e) ≥ Σ_{e∈B} Σ_{p sep. por e} y_p ≥ Σ_p y_p`,
porque cada pareja conflictiva es separada por algún `e ∈ B` (dualidad
débil del hitting set). Una pareja con un único separador fuerza ese
experimento en toda base (`forced_experiments`).

## Reproducción

```bash
export PYTHONPATH="$PWD"
python -m logic_power_fixed_basis_bound_v1.run_fixed_basis_bound_v1
python -m logic_power_fixed_basis_bound_v1.verify_fixed_basis_bound_v1 \
  certificates/fixed_basis_bound_or8.json
node logic_power_fixed_basis_bound_v1/verify_fixed_basis_bound_v1.js \
  certificates/fixed_basis_bound_or8.json
bash logic_power_fixed_basis_bound_v1/ci_v1.sh
```

El verificador Python añade `semantic-replay` (reconstrucción determinista
del análisis). El verificador Node es una segunda implementación sin
código compartido: no reconstruye ni enumera; todo dual factible es cota.

## Códigos de error

`certificate-shape` (falta `payload`/`sha256`); `payload-hash` (SHA-256 no
coincide); `schema` (esquema incorrecto); `problem-shape` (el problema no
se reconstruye); `obstruction` (obstrucción declarada ≠ recomputada);
`impossible-shape` (obstrucción con campos no nulos); `basis-cover` (la
base no separa alguna pareja); `basis-cost` (costo ≠ suma de la base);
`forced-experiments` (forzados ≠ recomputados); `forced-subset` (forzado
fuera de la base); `dual-shape` (pesos no canónicos o no positivos);
`dual-feasible` (capacidad de un experimento excedida); `dual-value`
(valor ≠ suma de pesos); `dual-bound` (valor > costo de la base);
`tight-flag` (marca ≠ igualdad valor/costo); `semantic-replay` (el
análisis no se reconstruye; sólo Python).

## Invariante TLA+ documentada, no modelada

`DualBoundSound == tight => fixed_basis_cost = dual_value`: si `tight` es
verdadera, costo de la base y valor dual coinciden. `tla_v10/` está
fijada por el manifiesto y su modelo (2 hipótesis, 1 experimento) no
representa la base fija: la invariante se enuncia aquí, sin model checking.
