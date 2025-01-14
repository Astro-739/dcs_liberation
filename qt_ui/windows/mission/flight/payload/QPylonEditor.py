import logging
import operator
from typing import Optional

from PySide6.QtWidgets import QComboBox

from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon


class QPylonEditor(QComboBox):
    def __init__(
        self, game: Game, flight: Flight, flight_member: FlightMember, pylon: Pylon
    ) -> None:
        super().__init__()
        self.flight = flight
        self.flight_member = flight_member
        self.pylon = pylon
        self.game = game
        self.has_added_clean_item = False

        current = self.flight_member.loadout.pylons.get(self.pylon.number)

        self.addItem("None", None)
        if self.game.settings.restrict_weapons_by_date:
            weapons = pylon.available_on(
                self.game.date, flight.squadron.coalition.faction
            )
        else:
            weapons = pylon.allowed
        allowed = sorted(weapons, key=operator.attrgetter("name"))
        for i, weapon in enumerate(allowed):
            self.addItem(weapon.name, weapon)
            if current == weapon:
                self.setCurrentIndex(i + 1)

        self.currentIndexChanged.connect(self.on_pylon_change)

    def on_pylon_change(self):
        selected: Optional[Weapon] = self.currentData()
        self.flight_member.loadout.pylons[self.pylon.number] = selected

        if selected is None:
            logging.debug(f"Pylon {self.pylon.number} emptied")
        else:
            logging.debug(f"Pylon {self.pylon.number} changed to {selected.name}")

    def weapon_from_loadout(self, loadout: Loadout) -> Optional[Weapon]:
        weapon = loadout.pylons.get(self.pylon.number)
        if weapon is None:
            return None
        # TODO: Fix pydcs to support the <CLEAN> "weapon".
        # These are not exported in the pydcs weapon map, which causes the pydcs pylon
        # exporter to fail to include them in the supported list. Since they aren't
        # known to be compatible (and we can't show them as compatible for *every*
        # pylon, because they aren't), we won't have populated a "Clean" weapon when
        # creating the selection list, so it's not selectable. To work around this, add
        # the item to the list the first time it's encountered for the pylon.
        #
        # A similar hack exists in Pylon to support forcibly equipping this even when
        # it's not known to be compatible.
        if weapon.clsid == "<CLEAN>":
            if not self.has_added_clean_item:
                self.addItem("Clean", weapon)
                self.has_added_clean_item = True
        return weapon

    def matching_weapon_name(self, loadout: Loadout) -> str:
        if self.game.settings.restrict_weapons_by_date:
            loadout = loadout.degrade_for_date(
                self.flight.unit_type,
                self.game.date,
                self.flight.squadron.coalition.faction,
            )
        weapon = self.weapon_from_loadout(loadout)
        if weapon is None:
            return "None"
        return weapon.name

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        self.set_from(self.flight_member.loadout)

    def set_from(self, loadout: Loadout) -> None:
        self.setCurrentText(self.matching_weapon_name(loadout))
