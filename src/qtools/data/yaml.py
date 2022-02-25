from uuid import UUID

import yaml
from yaml.constructor import ConstructorError
from yaml.error import YAMLError


def is_valid_uuid(s):
    try:
        UUID(s, version=4)
    except Exception:
        return False
    return True


class DomainYAMLObject(yaml.YAMLObject):
    @classmethod
    def from_yaml(cls, loader, node):
        try:
            pid = loader.construct_scalar(node)
            if not (hasattr(cls, "get_by_id") and callable(cls.get_by_id)):
                raise YAMLError(
                    f"Could not load {node.tag} from DB: Not loadable by pID."
                )
            if not is_valid_uuid(pid):
                raise YAMLError(
                    f"Could not load {node.tag} from DB: {pid} is not a valid UUID."
                )
            return cls.get_by_id(node.value)
        except ConstructorError:
            # No pid (scalar), try mapping
            try:
                # deep construct to catch all sub objects
                data = loader.construct_mapping(node, deep=True)
                return cls.create(**data)
            except ConstructorError:
                # No mapping, use super call
                return super().from_yaml(loader, node)

    @classmethod
    def to_yaml(cls, dumper, data):
        return super().to_yaml(dumper, data)
