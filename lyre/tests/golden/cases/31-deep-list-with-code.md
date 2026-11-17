- Backend
  - API
    - Add the route:

      ```python
      @app.get('/health')
      def health(): return {'ok': True}
      ```

- Frontend
  - Show the status badge ✅
