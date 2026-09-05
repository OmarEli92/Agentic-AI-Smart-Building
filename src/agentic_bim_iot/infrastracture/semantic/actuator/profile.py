from pydantic import BaseModel, ConfigDict, Field
class ActuatorOntologyProfile(BaseModel):
    """This is the ontological profile strategy in which instead of relying on a LLM call 
    we define the BOP actuator onotology profile, STILL dataset Agnostic BUT Ontology aware"""
    model_config = ConfigDict(extra="forbid", frozen="True")
    room_name_property: str = Field(min_length=1)
    acts_on_room_property: str = Field(min_length=1)
    acts_on_property: str = Field(min_length=1)
    guid_property: str = Field(min_length=1)
    actuator_root_class: str = Field(min_length=1)
    subclass_property: str = Field(min_length=1)
    measurement_types: dict[str, str] 
    
    
    
BOP_ACTUATOR_ONTOLOGY_PROFILE = ActuatorOntologyProfile(
room_name_property="https://w3id.org/props#longNameIfcSpatialStructureElement_attribute_simple",
acts_on_room_property="https://w3id.org/bop#actsOnRoom",
acts_on_property="https://w3id.org/bop#actsOn",
guid_property="https://w3id.org/bot#hasGuid",
actuator_root_class="https://w3id.org/bop#Actuator",
subclass_property="http://www.w3.org/2000/01/rdf-schema#subClassOf",
measurement_types={
    "temperature": "http://qudt.org/vocab/quantitykind/Temperature",
    "humidity": "http://qudt.org/vocab/quantitykind/RelativeHumidity",
    "brightness": "http://qudt.org/vocab/quantitykind/Illuminance",
},
)