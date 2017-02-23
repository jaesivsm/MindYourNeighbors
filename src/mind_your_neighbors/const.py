import re
import logging
from enum import Enum


class MatchResult(Enum):
    EXCLUDED = 'excluded'
    MATCHED = 'matched'
    NO_MATCH = 'no match'


REACHABLE = re.compile('.*REACHABLE.*')
KNOWN_MACHINES_SECTION = 'known_machines'
LOG_TO_MATCH_RES_MAPPING = ((logging.DEBUG, MatchResult.EXCLUDED),
                            (logging.INFO, MatchResult.MATCHED),
                            (logging.DEBUG, MatchResult.NO_MATCH))
