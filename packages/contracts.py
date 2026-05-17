from __future__ import annotations

from abc import ABC, abstractmethod

from packages.domain import DetectionRule, RiskLevel


class BaseContract(ABC):
    contract_type = "general"

    @classmethod
    @abstractmethod
    def get_rules(cls) -> tuple[DetectionRule, ...]:
        raise NotImplementedError

    @classmethod
    def get_focus(cls) -> str:
        return "Revisión contractual general"


class GeneralContract(BaseContract):
    contract_type = "general"

    @classmethod
    def get_rules(cls) -> tuple[DetectionRule, ...]:
        return ()


class RentalContract(BaseContract):
    contract_type = "rental"

    @classmethod
    def get_focus(cls) -> str:
        return "Detectar cláusulas contrarias a la LAU y desequilibrios en contratos de arrendamiento."

    @classmethod
    def get_rules(cls) -> tuple[DetectionRule, ...]:
        return (
            DetectionRule(
                label="reparaciones_estructurales_inquilino",
                terms=("estructura de muros", "tejados y fachadas", "red general de saneamiento", "art. 21 de la lau"),
                severity=RiskLevel.HIGH,
                recommendation="Revisar si se traslada al inquilino una obligación de conservación que corresponde al arrendador.",
            ),
            DetectionRule(
                label="acceso_ilimitado_arrendador",
                terms=("cuando quiera", "sin aviso previo", "podra entrar a inspeccionar"),
                severity=RiskLevel.HIGH,
                recommendation="Comprobar si se vulnera la intimidad domiciliaria del arrendatario.",
            ),
            DetectionRule(
                label="desahucio_privado",
                terms=("cambiar la cerradura", "sacar sus cosas a la calle", "desahucio express privado"),
                severity=RiskLevel.HIGH,
                recommendation="Invalidar cualquier autotutela privada y remitir a cauces judiciales legales.",
            ),
            DetectionRule(
                label="gastos_inmobiliaria_inquilino",
                terms=("gestion de la agencia", "gastos de inmobiliaria", "honorarios de la agencia"),
                severity=RiskLevel.MEDIUM,
                recommendation="Validar si se imponen al inquilino gastos que corresponden legalmente al arrendador.",
            ),
        )


class NDAContract(BaseContract):
    contract_type = "nda"

    @classmethod
    def get_focus(cls) -> str:
        return "Detectar duración excesiva, penalizaciones desproporcionadas y desequilibrios en acuerdos de confidencialidad."

    @classmethod
    def get_rules(cls) -> tuple[DetectionRule, ...]:
        return (
            DetectionRule(
                label="duracion_infinita",
                terms=("para siempre", "por toda la eternidad", "duracion indefinida absoluta"),
                severity=RiskLevel.HIGH,
                recommendation="Revisar si la obligación de confidencialidad tiene una duración razonable y proporcionada.",
            ),
            DetectionRule(
                label="multa_desproporcionada",
                terms=("50.000.000", "cincuenta millones", "embargo preventivo de todas sus cuentas"),
                severity=RiskLevel.HIGH,
                recommendation="Comprobar proporcionalidad de la penalización y respeto a la tutela judicial.",
            ),
            DetectionRule(
                label="objeto_difuso_confidencialidad",
                terms=("absolutamente todo", "todo lo que el trabajador piense o diga", "propiedad de la empresa"),
                severity=RiskLevel.MEDIUM,
                recommendation="Limitar con claridad qué información es confidencial y qué derechos se transfieren realmente.",
            ),
            DetectionRule(
                label="jurisdiccion_exotica",
                terms=("islas caiman", "tribunales de las islas caiman", "jurisdiccion extranjera exclusiva"),
                severity=RiskLevel.MEDIUM,
                recommendation="Revisar si la sumisión jurisdiccional genera un desequilibrio procesal abusivo.",
            ),
        )


def create_contract(contract_type: str) -> type[BaseContract]:
    mapping = {
        RentalContract.contract_type: RentalContract,
        NDAContract.contract_type: NDAContract,
        GeneralContract.contract_type: GeneralContract,
    }
    return mapping.get(contract_type, GeneralContract)

