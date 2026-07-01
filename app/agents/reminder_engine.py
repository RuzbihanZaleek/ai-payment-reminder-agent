from datetime import date, timedelta
from decimal import Decimal

class ReminderEngine:
    
    def calculate_pending_amount( self, total_amount: Decimal, total_paid: Decimal ):
        remaining = total_amount - total_paid
        return max( remaining, Decimal("0") ) 
    
    def calculate_pending_days( self, daily_amount: Decimal, remaining_amount: Decimal ):
        
        if daily_amount <= 0:
            raise ValueError("Daily amount must be greater than zero")
        
        return int(remaining_amount / daily_amount)
    
    def calculate_pending_dates(
        self,
        last_covered_date: date,
        today: date,
        daily_amount: Decimal,
        remaining_amount: Decimal
    ) -> list[date]:

        pending_days = self.calculate_pending_days(
            daily_amount,
            remaining_amount
        )

        dates = []

        current_date = last_covered_date + timedelta(days=1)

        while current_date <= today and len(dates) < pending_days:
            dates.append(current_date)
            current_date += timedelta(days=1)

        return dates
    
    def build_reminder_context(
        self,
        last_covered_date: date,
        today: date,
        total_amount: Decimal,
        total_paid: Decimal,
        daily_amount: Decimal
    ):

        remaining_amount = self.calculate_pending_amount(
            total_amount,
            total_paid
        )

        pending_dates = self.calculate_pending_dates(
            last_covered_date,
            today,
            daily_amount,
            remaining_amount
        )

        return {
            "pending_dates": pending_dates,
            "pending_amount": (
                daily_amount * len(pending_dates)
            )
        }        