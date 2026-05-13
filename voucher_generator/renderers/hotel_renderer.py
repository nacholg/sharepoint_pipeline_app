from typing import Any, Dict, List

from voucher_generator.renderers.common import (
    e,
    display_or_pending,
    no_break_iso_date,
)

def room_rows(rooms: List[Dict[str, Any]], t: dict[str, str]) -> str:
    rows: List[str] = []
    for room in rooms:
        rows.append(
            f"""
            <tr>
              <td>{display_or_pending(room.get('room_count'), t['empty'])}</td>
              <td class="text-wrap">{display_or_pending(room.get('room_category'), t['empty'])}</td>
              <td class="text-wrap">{display_or_pending(room.get('additional_info'), t['empty'])}</td>
              <td>{display_or_pending(room.get('pax_count'), t['empty'])}</td>
            </tr>
            """
        )
    return "\n".join(rows) or f'<tr><td colspan="4">{e(t["no_rooming_details"])}</td></tr>'

def passenger_cards(passengers: List[Dict[str, Any]], t: dict[str, str], language: str) -> str:
    cards: List[str] = []
    for pax in passengers:
        nationality_html = display_or_pending(pax.get("nationality"), t["empty"])
        passport_html = display_or_pending(pax.get("passport_number"), t["empty"])
        expiration_html = display_or_pending(pax.get("passport_expiration"), t["empty"])
        if pax.get("passport_expiration") not in (None, ""):
            expiration_html = no_break_iso_date(pax.get("passport_expiration"), language=language)

        cards.append(
            f"""
            <article class="pax-card">
              <div class="pax-name">{e(pax.get('full_name') or t['passenger_fallback'])}</div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["nationality"])}</span><span class="pax-value">{nationality_html}</span></div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["passport"])}</span><span class="pax-value">{passport_html}</span></div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["passport_expiry"])}</span><span class="pax-value">{expiration_html}</span></div>
            </article>
            """
        )
    return "\n".join(cards) or f'<div class="empty-state">{e(t["no_passengers_loaded"])}</div>'

def rooms_section(rooms: List[Dict[str, Any]], t: Dict[str, str]) -> str:
    return f"""
      <section class="panel rooms-panel">
        <button class="section-title section-toggle" type="button" onclick="this.closest('.rooms-panel').classList.toggle('is-collapsed')">
          {e(t["room_details"])}
        </button>

        <div class="section-collapsible-body">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{e(t["rooms"])}</th>
                  <th>{e(t["category"])}</th>
                  <th>{e(t["additional_info"])}</th>
                  <th>{e(t["passengers"])}</th>
                </tr>
              </thead>
              <tbody>
                {room_rows(rooms, t)}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    """


def passengers_section(
    passengers: List[Dict[str, Any]],
    t: Dict[str, str],
    language: str,
) -> str:
    return f"""
      <section class="panel passengers-panel">
        <button class="section-title section-toggle" type="button" onclick="this.closest('.passengers-panel').classList.toggle('is-collapsed')">
          {e(t["passengers"])}
        </button>

        <div class="section-collapsible-body">
          <div class="passengers-grid">
            {passenger_cards(passengers, t, language)}
          </div>
        </div>
      </section>
    """